import csv
import io
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from app import storage
from app.models import System
from app.permissions import (
    validate_and_get_user,
    check_is_applicant,
    check_not_applicant_for_review,
    check_not_applicant_for_approval,
    PermissionError,
    ROLES
)
from app.state_validator import (
    validate_transition,
    validate_risk_level,
    validate_window,
    validate_window_conflict,
    validate_review_before_approval,
    validate_withdraw_before_effective,
    validate_re_effective,
    StateValidationError
)

bp = Blueprint('api', __name__)


def error_response(message, code, status_code=400):
    return jsonify({
        'success': False,
        'error': {
            'code': code,
            'message': message
        }
    }), status_code


def success_response(data=None, message=None):
    result = {'success': True}
    if data is not None:
        result['data'] = data
    if message is not None:
        result['message'] = message
    return jsonify(result), 200


def serialize_request(req):
    return {
        'id': req.id,
        'title': req.title,
        'system': {
            'id': req.system.id,
            'name': req.system.name,
            'description': req.system.description
        } if req.system else None,
        'applicant': {
            'id': req.applicant.id,
            'username': req.applicant.username,
            'role': req.applicant.role.name
        } if req.applicant else None,
        'reviewer': {
            'id': req.reviewer.id,
            'username': req.reviewer.username,
            'role': req.reviewer.role.name
        } if req.reviewer else None,
        'approver': {
            'id': req.approver.id,
            'username': req.approver.username,
            'role': req.approver.role.name
        } if req.approver else None,
        'window_start': req.window_start.isoformat() + 'Z',
        'window_end': req.window_end.isoformat() + 'Z',
        'risk_level': req.risk_level,
        'reason': req.reason,
        'remark': req.remark,
        'status': req.status,
        'review_comment': req.review_comment,
        'approval_comment': req.approval_comment,
        'created_at': req.created_at.isoformat() + 'Z',
        'updated_at': req.updated_at.isoformat() + 'Z'
    }


def serialize_history(h):
    return {
        'id': h.id,
        'request_id': h.request_id,
        'from_status': h.from_status,
        'to_status': h.to_status,
        'operator': {
            'id': h.operator.id,
            'username': h.operator.username,
            'role': h.operator.role.name
        } if h.operator else None,
        'batch': {
            'id': h.batch.id,
            'batch_no': h.batch.batch_no
        } if h.batch else None,
        'comment': h.comment,
        'created_at': h.created_at.isoformat() + 'Z'
    }


@bp.route('/roles', methods=['GET'])
def get_roles():
    try:
        roles = storage.get_all_roles()
        return success_response([{
            'id': r.id,
            'name': r.name,
            'description': r.description,
            'display_name': ROLES.get(r.name, r.name)
        } for r in roles])
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/systems', methods=['GET'])
def get_systems():
    try:
        systems = storage.get_all_systems()
        return success_response([{
            'id': s.id,
            'name': s.name,
            'description': s.description
        } for s in systems])
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests', methods=['POST'])
def create_request():
    try:
        data = request.get_json()
        if not data:
            return error_response('请求体不能为空', 'EMPTY_BODY')

        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'create_request')

        required_fields = ['system_id', 'window_start', 'window_end', 'risk_level', 'reason']
        for field in required_fields:
            if field not in data:
                return error_response(f'缺少必填字段: {field}', f'MISSING_{field.upper()}')

        system_id = data['system_id']
        system = storage.get_system_by_name(system_id) if isinstance(system_id, str) else None
        if not system and isinstance(system_id, int):
            system = System.query.get(system_id)
        if not system:
            return error_response(f'系统不存在: {system_id}', 'SYSTEM_NOT_FOUND')

        window_start, window_end = validate_window(data['window_start'], data['window_end'])
        validate_risk_level(data['risk_level'])
        validate_window_conflict(system.id, window_start, window_end)

        req = storage.create_request(
            system_id=system.id,
            applicant_id=user.id,
            window_start=window_start,
            window_end=window_end,
            risk_level=data['risk_level'],
            reason=data['reason'],
            title=data.get('title'),
            remark=data.get('remark')
        )

        return success_response(serialize_request(req), '申请提交成功')
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except StateValidationError as e:
        return error_response(e.message, e.code, 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests', methods=['GET'])
def get_requests():
    try:
        data = request.args
        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'view_requests')

        requests = storage.get_visible_requests(user)
        return success_response([serialize_request(r) for r in requests])
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/<int:request_id>', methods=['GET'])
def get_request(request_id):
    try:
        data = request.args
        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        validate_and_get_user(username, 'view_requests')

        req = storage.get_request_by_id(request_id)
        if not req:
            return error_response(f'申请不存在: {request_id}', 'REQUEST_NOT_FOUND', 404)

        return success_response(serialize_request(req))
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/<int:request_id>/review', methods=['POST'])
def review_request(request_id):
    try:
        data = request.get_json()
        if not data:
            return error_response('请求体不能为空', 'EMPTY_BODY')

        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'review_request')

        req = storage.get_request_by_id(request_id)
        if not req:
            return error_response(f'申请不存在: {request_id}', 'REQUEST_NOT_FOUND', 404)

        check_not_applicant_for_review(user, req)

        approved = data.get('approved', True)
        comment = data.get('comment', '')

        if approved:
            validate_transition(req.status, 'REVIEWED')
            storage.set_reviewer(request_id, user.id, comment)
            storage.update_request_status(request_id, 'REVIEWED', user.id, comment or '风险复核通过')
        else:
            validate_transition(req.status, 'REVIEW_REJECTED')
            storage.set_reviewer(request_id, user.id, comment)
            storage.update_request_status(request_id, 'REVIEW_REJECTED', user.id, comment or '风险复核拒绝')

        req = storage.get_request_by_id(request_id)
        return success_response(serialize_request(req), '复核完成')
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except StateValidationError as e:
        return error_response(e.message, e.code, 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/<int:request_id>/approve', methods=['POST'])
def approve_request(request_id):
    try:
        data = request.get_json()
        if not data:
            return error_response('请求体不能为空', 'EMPTY_BODY')

        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'approve_request')

        req = storage.get_request_by_id(request_id)
        if not req:
            return error_response(f'申请不存在: {request_id}', 'REQUEST_NOT_FOUND', 404)

        check_not_applicant_for_approval(user, req)
        validate_review_before_approval(req.status)
        validate_transition(req.status, 'APPROVED')

        validate_window_conflict(req.system_id, req.window_start, req.window_end, request_id)

        comment = data.get('comment', '')
        storage.set_approver(request_id, user.id, comment)
        storage.update_request_status(request_id, 'APPROVED', user.id, comment or '审批通过')

        req = storage.get_request_by_id(request_id)
        return success_response(serialize_request(req), '审批通过')
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except StateValidationError as e:
        return error_response(e.message, e.code, 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/<int:request_id>/effective', methods=['POST'])
def effective_request(request_id):
    try:
        data = request.get_json()
        if not data:
            return error_response('请求体不能为空', 'EMPTY_BODY')

        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'approve_request')

        req = storage.get_request_by_id(request_id)
        if not req:
            return error_response(f'申请不存在: {request_id}', 'REQUEST_NOT_FOUND', 404)

        validate_transition(req.status, 'EFFECTIVE')
        validate_window_conflict(req.system_id, req.window_start, req.window_end, request_id)

        comment = data.get('comment', '')
        storage.update_request_status(request_id, 'EFFECTIVE', user.id, comment or '变更已生效')

        req = storage.get_request_by_id(request_id)
        return success_response(serialize_request(req), '变更已生效')
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except StateValidationError as e:
        return error_response(e.message, e.code, 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/<int:request_id>/withdraw', methods=['POST'])
def withdraw_request(request_id):
    try:
        data = request.get_json()
        if not data:
            return error_response('请求体不能为空', 'EMPTY_BODY')

        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'withdraw_request')

        req = storage.get_request_by_id(request_id)
        if not req:
            return error_response(f'申请不存在: {request_id}', 'REQUEST_NOT_FOUND', 404)

        check_is_applicant(user, req)
        validate_withdraw_before_effective(req.status)
        validate_transition(req.status, 'WITHDRAWN')

        comment = data.get('comment', '')
        storage.update_request_status(request_id, 'WITHDRAWN', user.id, comment or '申请人撤回')

        req = storage.get_request_by_id(request_id)
        return success_response(serialize_request(req), '申请已撤回')
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except StateValidationError as e:
        return error_response(e.message, e.code, 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/<int:request_id>/re-effective', methods=['POST'])
def re_effective_request(request_id):
    try:
        data = request.get_json()
        if not data:
            return error_response('请求体不能为空', 'EMPTY_BODY')

        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 're_effective_request')

        req = storage.get_request_by_id(request_id)
        if not req:
            return error_response(f'申请不存在: {request_id}', 'REQUEST_NOT_FOUND', 404)

        validate_re_effective(req.status)
        validate_transition(req.status, 'APPROVED')
        validate_window_conflict(req.system_id, req.window_start, req.window_end, request_id)

        comment = data.get('comment', '')
        storage.update_request_status(request_id, 'APPROVED', user.id, comment or '撤回后再次批准')

        req = storage.get_request_by_id(request_id)
        return success_response(serialize_request(req), '已再次批准')
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except StateValidationError as e:
        return error_response(e.message, e.code, 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/audit', methods=['GET'])
def get_audit_log():
    try:
        data = request.args
        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        validate_and_get_user(username, 'view_audit')

        request_id_param = data.get('request_id')
        request_id = None
        if request_id_param is not None and request_id_param != '':
            try:
                request_id = int(request_id_param)
            except ValueError:
                return error_response(
                    f'request_id 参数无效，必须是整数: {request_id_param}',
                    'INVALID_REQUEST_ID',
                    400
                )

            req = storage.get_request_by_id(request_id)
            if not req:
                return error_response(
                    f'申请不存在: {request_id}',
                    'REQUEST_NOT_FOUND',
                    404
                )

        history = storage.get_all_status_history(request_id)
        return success_response([serialize_history(h) for h in history])
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/<int:request_id>/history', methods=['GET'])
def get_request_history(request_id):
    try:
        data = request.args
        username = data.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        validate_and_get_user(username, 'view_audit')

        req = storage.get_request_by_id(request_id)
        if not req:
            return error_response(f'申请不存在: {request_id}', 'REQUEST_NOT_FOUND', 404)

        history = storage.get_status_history_by_request(request_id)
        return success_response([serialize_history(h) for h in history])
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/users', methods=['GET'])
def get_users():
    try:
        from app.models import User
        users = User.query.all()
        return success_response([{
            'id': u.id,
            'username': u.username,
            'role': {
                'id': u.role.id,
                'name': u.role.name,
                'display_name': ROLES.get(u.role.name, u.role.name)
            }
        } for u in users])
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/export', methods=['GET'])
def export_requests():
    try:
        username = request.args.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'export_requests')

        requests = storage.get_visible_requests(user)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            '标题', '系统', '窗口开始', '窗口结束',
            '风险等级', '风险说明', '备注'
        ])

        for req in requests:
            writer.writerow([
                req.title,
                req.system.name,
                req.window_start.isoformat() + 'Z',
                req.window_end.isoformat() + 'Z',
                req.risk_level,
                req.reason,
                req.remark or ''
            ])

        output.seek(0)
        filename = f'change_requests_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/requests/import', methods=['POST'])
def import_requests():
    try:
        username = request.form.get('username') or request.args.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'import_requests')

        if 'file' not in request.files:
            return error_response('缺少文件参数', 'MISSING_FILE')

        file = request.files['file']
        if file.filename == '':
            return error_response('文件名为空', 'EMPTY_FILENAME')

        if not file.filename.endswith('.csv'):
            return error_response('只支持 CSV 格式文件', 'INVALID_FILE_FORMAT')

        stream = io.TextIOWrapper(file.stream, encoding='utf-8-sig')
        reader = csv.DictReader(stream)

        required_columns = ['标题', '系统', '窗口开始', '窗口结束', '风险等级', '风险说明']
        for col in required_columns:
            if col not in reader.fieldnames:
                return error_response(f'缺少必填列: {col}', 'MISSING_COLUMN')

        rows = list(reader)
        total_count = len(rows)

        if total_count == 0:
            return error_response('CSV 文件为空', 'EMPTY_FILE')

        batch_no = f'IMP_{datetime.now().strftime("%Y%m%d%H%M%S")}_{uuid.uuid4().hex[:8]}'
        batch = storage.create_import_batch(batch_no, user.id, total_count)

        success_count = 0
        fail_count = 0
        failed_rows = []
        success_ids = []

        for idx, row in enumerate(rows, start=2):
            try:
                title = row.get('标题', '').strip()
                system_name = row.get('系统', '').strip()
                window_start_str = row.get('窗口开始', '').strip()
                window_end_str = row.get('窗口结束', '').strip()
                risk_level = row.get('风险等级', '').strip()
                reason = row.get('风险说明', '').strip()
                remark = row.get('备注', '').strip()

                if not title:
                    raise StateValidationError('标题不能为空', 'MISSING_TITLE')
                if not system_name:
                    raise StateValidationError('系统不能为空', 'MISSING_SYSTEM')
                if not window_start_str:
                    raise StateValidationError('窗口开始不能为空', 'MISSING_WINDOW_START')
                if not window_end_str:
                    raise StateValidationError('窗口结束不能为空', 'MISSING_WINDOW_END')
                if not risk_level:
                    raise StateValidationError('风险等级不能为空', 'MISSING_RISK_LEVEL')
                if not reason:
                    raise StateValidationError('风险说明不能为空', 'MISSING_REASON')

                system = storage.get_system_by_name(system_name)
                if not system:
                    raise StateValidationError(f'系统不存在: {system_name}', 'SYSTEM_NOT_FOUND')

                window_start, window_end = validate_window(window_start_str, window_end_str)
                validate_risk_level(risk_level)
                validate_window_conflict(system.id, window_start, window_end)

                req = storage.create_request(
                    system_id=system.id,
                    applicant_id=user.id,
                    window_start=window_start,
                    window_end=window_end,
                    risk_level=risk_level,
                    reason=reason,
                    title=title,
                    remark=remark,
                    batch_id=batch.id
                )

                storage.create_import_record(batch.id, idx, True, request_id=req.id)
                success_count += 1
                success_ids.append(req.id)

            except (StateValidationError, PermissionError) as e:
                fail_count += 1
                failed_rows.append({
                    'row': idx,
                    'code': e.code,
                    'message': e.message
                })
                storage.create_import_record(
                    batch.id, idx, False,
                    error_code=e.code,
                    error_message=e.message
                )
            except Exception as e:
                fail_count += 1
                failed_rows.append({
                    'row': idx,
                    'code': 'INTERNAL_ERROR',
                    'message': str(e)
                })
                storage.create_import_record(
                    batch.id, idx, False,
                    error_code='INTERNAL_ERROR',
                    error_message=str(e)
                )

        storage.update_import_batch(batch.id, success_count, fail_count)

        return success_response({
            'batch_no': batch_no,
            'total_count': total_count,
            'success_count': success_count,
            'fail_count': fail_count,
            'success_ids': success_ids,
            'failed_rows': failed_rows
        }, f'导入完成：成功 {success_count} 条，失败 {fail_count} 条')

    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except StateValidationError as e:
        return error_response(e.message, e.code, 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/import/batches', methods=['GET'])
def get_import_batches():
    try:
        username = request.args.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'view_audit')

        batches = storage.get_all_import_batches()
        return success_response([{
            'id': b.id,
            'batch_no': b.batch_no,
            'operator': {
                'id': b.operator.id,
                'username': b.operator.username,
                'role': b.operator.role.name
            } if b.operator else None,
            'total_count': b.total_count,
            'success_count': b.success_count,
            'fail_count': b.fail_count,
            'created_at': b.created_at.isoformat() + 'Z'
        } for b in batches])
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@bp.route('/import/batches/<string:batch_no>/records', methods=['GET'])
def get_import_batch_records(batch_no):
    try:
        username = request.args.get('username')
        if not username:
            return error_response('缺少 username 参数', 'MISSING_USERNAME')

        user = validate_and_get_user(username, 'view_audit')

        batch = storage.get_import_batch_by_no(batch_no)
        if not batch:
            return error_response(f'批次不存在: {batch_no}', 'BATCH_NOT_FOUND', 404)

        records = storage.get_import_records_by_batch(batch.id)
        return success_response({
            'batch': {
                'id': batch.id,
                'batch_no': batch.batch_no,
                'operator': {
                    'id': batch.operator.id,
                    'username': batch.operator.username,
                    'role': batch.operator.role.name
                } if batch.operator else None,
                'total_count': batch.total_count,
                'success_count': batch.success_count,
                'fail_count': batch.fail_count,
                'created_at': batch.created_at.isoformat() + 'Z'
            },
            'records': [{
                'row_no': r.row_no,
                'success': r.success,
                'error_code': r.error_code,
                'error_message': r.error_message,
                'request_id': r.request_id
            } for r in records]
        })
    except PermissionError as e:
        return error_response(e.message, e.code, 403)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)
