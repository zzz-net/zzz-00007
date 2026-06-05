from app import storage


ROLES = {
    'APPLICANT': '申请人',
    'REVIEWER': '风险复核人',
    'APPROVER': '审批人'
}

PERMISSIONS = {
    'create_request': ['APPLICANT'],
    'review_request': ['REVIEWER'],
    'approve_request': ['APPROVER'],
    'withdraw_request': ['APPLICANT'],
    're_effective_request': ['APPROVER'],
    'view_audit': ['APPLICANT', 'REVIEWER', 'APPROVER'],
    'view_requests': ['APPLICANT', 'REVIEWER', 'APPROVER']
}


class PermissionError(Exception):
    def __init__(self, message, code='PERMISSION_DENIED'):
        self.message = message
        self.code = code
        super().__init__(self.message)


def authenticate_user(username):
    user = storage.get_user_by_username(username)
    if not user:
        raise PermissionError(
            f'用户不存在: {username}',
            'USER_NOT_FOUND'
        )
    return user


def check_role_permission(user, action):
    role_name = user.role.name
    allowed_roles = PERMISSIONS.get(action, [])
    if role_name not in allowed_roles:
        allowed_role_names = [ROLES.get(r, r) for r in allowed_roles]
        raise PermissionError(
            f'角色 "{ROLES.get(role_name, role_name)}" 无权执行此操作。'
            f'允许的角色: {", ".join(allowed_role_names)}',
            'ROLE_PERMISSION_DENIED'
        )


def check_is_applicant(user, request):
    if user.id != request.applicant_id:
        raise PermissionError(
            '只有申请人本人才能执行此操作',
            'NOT_APPLICANT'
        )


def check_not_applicant_for_review(user, request):
    if user.id == request.applicant_id:
        raise PermissionError(
            '申请人不能复核自己的申请',
            'APPLICANT_CANNOT_REVIEW'
        )


def check_not_applicant_for_approval(user, request):
    if user.id == request.applicant_id:
        raise PermissionError(
            '申请人不能批准自己的申请',
            'APPLICANT_CANNOT_APPROVE'
        )


def validate_and_get_user(username, action):
    user = authenticate_user(username)
    check_role_permission(user, action)
    return user
