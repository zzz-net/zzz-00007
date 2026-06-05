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
    status = db.Column(db.String(30), nullable=False, default='PENDING_REVIEW')
    review_comment = db.Column(db.String(500))
    approval_comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('change_requests.id'), nullable=False)
    request = db.relationship('ChangeRequest', backref='status_history')
    from_status = db.Column(db.String(30))
    to_status = db.Column(db.String(30), nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operator = db.relationship('User', backref='status_operations')
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
