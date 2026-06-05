from datetime import datetime
from app import storage


VALID_STATUSES = [
    'PENDING_REVIEW',
    'REVIEWED',
    'REVIEW_REJECTED',
    'APPROVED',
    'EFFECTIVE',
    'WITHDRAWN'
]

VALID_TRANSITIONS = {
    'PENDING_REVIEW': ['REVIEWED', 'REVIEW_REJECTED', 'WITHDRAWN'],
    'REVIEWED': ['APPROVED', 'REVIEW_REJECTED', 'WITHDRAWN'],
    'REVIEW_REJECTED': ['WITHDRAWN'],
    'APPROVED': ['EFFECTIVE', 'WITHDRAWN'],
    'EFFECTIVE': ['WITHDRAWN'],
    'WITHDRAWN': ['APPROVED']
}

RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']


class StateValidationError(Exception):
    def __init__(self, message, code='STATE_VALIDATION_ERROR'):
        self.message = message
        self.code = code
        super().__init__(self.message)


def validate_status(status):
    if status not in VALID_STATUSES:
        raise StateValidationError(
            f'无效状态: {status}。允许的状态: {", ".join(VALID_STATUSES)}',
            'INVALID_STATUS'
        )


def validate_transition(from_status, to_status):
    validate_status(from_status)
    validate_status(to_status)
    if to_status not in VALID_TRANSITIONS.get(from_status, []):
        raise StateValidationError(
            f'不允许的状态转换: {from_status} -> {to_status}。'
            f'{from_status} 允许转换到: {", ".join(VALID_TRANSITIONS.get(from_status, []))}',
            'INVALID_TRANSITION'
        )


def validate_risk_level(risk_level):
    if risk_level not in RISK_LEVELS:
        raise StateValidationError(
            f'无效风险等级: {risk_level}。允许的等级: {", ".join(RISK_LEVELS)}',
            'INVALID_RISK_LEVEL'
        )


def validate_window(window_start_str, window_end_str):
    import re
    iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$'
    
    if not re.match(iso8601_pattern, window_start_str) or not re.match(iso8601_pattern, window_end_str):
        raise StateValidationError(
            '日期时间格式无效，请使用 ISO 8601 完整格式 (如: 2026-06-10T00:00:00Z)',
            'INVALID_DATETIME_FORMAT'
        )
    
    try:
        window_start = datetime.fromisoformat(window_start_str.replace('Z', '+00:00'))
        window_end = datetime.fromisoformat(window_end_str.replace('Z', '+00:00'))
    except ValueError:
        raise StateValidationError(
            '日期时间格式无效，请使用 ISO 8601 完整格式 (如: 2026-06-10T00:00:00Z)',
            'INVALID_DATETIME_FORMAT'
        )

    if window_start >= window_end:
        raise StateValidationError(
            '窗口期开始时间必须早于结束时间',
            'INVALID_WINDOW_RANGE'
        )

    return window_start, window_end


def validate_window_conflict(system_id, window_start, window_end, exclude_request_id=None):
    if storage.check_window_conflict(system_id, window_start, window_end, exclude_request_id):
        raise StateValidationError(
            '该系统在申请的窗口期内已有已批准或已生效的变更冻结例外，窗口重叠',
            'WINDOW_CONFLICT'
        )


def validate_review_before_approval(request_status):
    if request_status == 'PENDING_REVIEW':
        raise StateValidationError(
            '申请尚未经过风险复核，审批人无法批准。请先由复核人进行风险复核',
            'NOT_REVIEWED'
        )
    if request_status == 'REVIEW_REJECTED':
        raise StateValidationError(
            '申请已被复核拒绝，无法批准',
            'REVIEW_REJECTED'
        )


def validate_withdraw_before_effective(request_status):
    if request_status == 'EFFECTIVE':
        raise StateValidationError(
            '申请已生效，无法撤回。如需停止，请联系管理员',
            'ALREADY_EFFECTIVE'
        )


def validate_re_effective(request_status):
    if request_status != 'WITHDRAWN':
        raise StateValidationError(
            '只有已撤回的申请才能再次生效',
            'NOT_WITHDRAWN'
        )
