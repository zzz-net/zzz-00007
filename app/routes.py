from flask import Blueprint, request, jsonify
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
            reason=data['reason']
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

        validate_and_get_user(username, 'view_requests')

        requests = storage.get_all_requests()
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

        history = storage.get_all_status_history()
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
