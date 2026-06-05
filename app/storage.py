from datetime import datetime
from app import db
from app.models import Role, System, User, ChangeRequest, StatusHistory, ImportBatch, ImportRecord


def get_role_by_name(name):
    return Role.query.filter_by(name=name).first()


def get_all_roles():
    return Role.query.all()


def create_role(name, description=None):
    role = Role(name=name, description=description)
    db.session.add(role)
    db.session.commit()
    return role


def get_system_by_name(name):
    return System.query.filter_by(name=name).first()


def get_all_systems():
    return System.query.all()


def create_system(name, description=None):
    system = System(name=name, description=description)
    db.session.add(system)
    db.session.commit()
    return system


def get_user_by_username(username):
    return User.query.filter_by(username=username).first()


def create_user(username, role_id):
    user = User(username=username, role_id=role_id)
    db.session.add(user)
    db.session.commit()
    return user


def get_request_by_id(request_id):
    return ChangeRequest.query.get(request_id)


def get_all_requests():
    return ChangeRequest.query.order_by(ChangeRequest.created_at.desc()).all()


def create_request(system_id, applicant_id, window_start, window_end, risk_level, reason, title=None, remark=None, batch_id=None):
    request = ChangeRequest(
        title=title or f'{risk_level}级变更-{system_id}',
        system_id=system_id,
        applicant_id=applicant_id,
        window_start=window_start,
        window_end=window_end,
        risk_level=risk_level,
        reason=reason,
        remark=remark,
        status='PENDING_REVIEW'
    )
    db.session.add(request)
    db.session.flush()
    add_status_history(request.id, None, 'PENDING_REVIEW', applicant_id, '提交申请', batch_id)
    db.session.commit()
    return request


def update_request_status(request_id, new_status, operator_id, comment=None):
    request = ChangeRequest.query.get(request_id)
    old_status = request.status
    request.status = new_status
    add_status_history(request_id, old_status, new_status, operator_id, comment)
    db.session.commit()
    return request


def set_reviewer(request_id, reviewer_id, comment=None):
    request = ChangeRequest.query.get(request_id)
    request.reviewer_id = reviewer_id
    request.review_comment = comment
    db.session.commit()
    return request


def set_approver(request_id, approver_id, comment=None):
    request = ChangeRequest.query.get(request_id)
    request.approver_id = approver_id
    request.approval_comment = comment
    db.session.commit()
    return request


def add_status_history(request_id, from_status, to_status, operator_id, comment=None, batch_id=None):
    history = StatusHistory(
        request_id=request_id,
        from_status=from_status,
        to_status=to_status,
        operator_id=operator_id,
        batch_id=batch_id,
        comment=comment
    )
    db.session.add(history)
    return history


def get_status_history_by_request(request_id):
    return StatusHistory.query.filter_by(request_id=request_id).order_by(StatusHistory.created_at.asc()).all()


def get_all_status_history(request_id=None):
    query = StatusHistory.query
    if request_id is not None:
        query = query.filter_by(request_id=request_id)
    return query.order_by(StatusHistory.created_at.desc()).all()


def check_window_conflict(system_id, window_start, window_end, exclude_request_id=None):
    query = ChangeRequest.query.filter(
        ChangeRequest.system_id == system_id,
        ChangeRequest.status.in_(['APPROVED', 'EFFECTIVE']),
        ChangeRequest.window_start < window_end,
        ChangeRequest.window_end > window_start
    )
    if exclude_request_id:
        query = query.filter(ChangeRequest.id != exclude_request_id)
    return query.first() is not None


def get_visible_requests(user):
    role_name = user.role.name
    if role_name == 'APPLICANT':
        return ChangeRequest.query.filter_by(
            applicant_id=user.id
        ).order_by(ChangeRequest.created_at.desc()).all()
    else:
        return ChangeRequest.query.order_by(ChangeRequest.created_at.desc()).all()


def create_import_batch(batch_no, operator_id, total_count=0):
    batch = ImportBatch(
        batch_no=batch_no,
        operator_id=operator_id,
        total_count=total_count,
        success_count=0,
        fail_count=0
    )
    db.session.add(batch)
    db.session.commit()
    return batch


def update_import_batch(batch_id, success_count, fail_count):
    batch = ImportBatch.query.get(batch_id)
    batch.success_count = success_count
    batch.fail_count = fail_count
    db.session.commit()
    return batch


def get_import_batch_by_no(batch_no):
    return ImportBatch.query.filter_by(batch_no=batch_no).first()


def create_import_record(batch_id, row_no, success, error_code=None, error_message=None, request_id=None):
    record = ImportRecord(
        batch_id=batch_id,
        row_no=row_no,
        success=success,
        error_code=error_code,
        error_message=error_message,
        request_id=request_id
    )
    db.session.add(record)
    db.session.commit()
    return record


def get_import_records_by_batch(batch_id):
    return ImportRecord.query.filter_by(batch_id=batch_id).order_by(ImportRecord.row_no.asc()).all()


def get_import_batch_by_id(batch_id):
    return ImportBatch.query.get(batch_id)


def get_all_import_batches():
    return ImportBatch.query.order_by(ImportBatch.created_at.desc()).all()
