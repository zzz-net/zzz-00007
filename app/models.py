from datetime import datetime
from app import db


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))


class System(db.Model):
    __tablename__ = 'systems'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500))


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    role = db.relationship('Role', backref='users')


class ChangeRequest(db.Model):
    __tablename__ = 'change_requests'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    system_id = db.Column(db.Integer, db.ForeignKey('systems.id'), nullable=False)
    system = db.relationship('System', backref='requests')
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    applicant = db.relationship('User', backref='requests', foreign_keys=[applicant_id])
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer = db.relationship('User', backref='reviewed_requests', foreign_keys=[reviewer_id])
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approver = db.relationship('User', backref='approved_requests', foreign_keys=[approver_id])
    window_start = db.Column(db.DateTime, nullable=False)
    window_end = db.Column(db.DateTime, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(1000), nullable=False)
    remark = db.Column(db.String(500))
    status = db.Column(db.String(30), nullable=False, default='PENDING_REVIEW')
    review_comment = db.Column(db.String(500))
    approval_comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ImportBatch(db.Model):
    __tablename__ = 'import_batches'
    id = db.Column(db.Integer, primary_key=True)
    batch_no = db.Column(db.String(50), unique=True, nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operator = db.relationship('User', backref='import_batches')
    total_count = db.Column(db.Integer, nullable=False, default=0)
    success_count = db.Column(db.Integer, nullable=False, default=0)
    fail_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ImportRecord(db.Model):
    __tablename__ = 'import_records'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('import_batches.id'), nullable=False)
    batch = db.relationship('ImportBatch', backref='records')
    row_no = db.Column(db.Integer, nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    error_code = db.Column(db.String(50))
    error_message = db.Column(db.String(500))
    request_id = db.Column(db.Integer, db.ForeignKey('change_requests.id'))
    request = db.relationship('ChangeRequest', backref='import_records')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('change_requests.id'), nullable=False)
    request = db.relationship('ChangeRequest', backref='status_history')
    from_status = db.Column(db.String(30))
    to_status = db.Column(db.String(30), nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operator = db.relationship('User', backref='status_operations')
    batch_id = db.Column(db.Integer, db.ForeignKey('import_batches.id'))
    batch = db.relationship('ImportBatch', backref='status_history')
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
