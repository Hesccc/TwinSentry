from datetime import datetime
from . import db, bcrypt
import enum

class AlertStatus(enum.Enum):
    PENDING = "待分析"
    ANALYZING = "分析中"
    ANALYZED = "已分析"
    PROCESSING = "处置中"
    PROCESSED = "已处置"

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), default='admin@twinsentry.local')
    avatar = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.JSON, nullable=False)  # Parsed list from \r\n
    raw_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default=AlertStatus.PENDING.value)
    analysis_result = db.Column(db.Text, nullable=True)
    process_result = db.Column(db.Text, nullable=True)
    analysis_time = db.Column(db.DateTime, nullable=True)
    process_time = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.Integer, default=2) # 1: High, 2: Medium, 3: Low
    is_delete = db.Column(db.Integer, default=0) # 0: False, 1: True
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False) # LOGIN, AGENT_FETCH_DATA, DATA_INPUT
    status = db.Column(db.String(32), nullable=False) # Success, Failed
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class NotificationConfig(db.Model):
    __tablename__ = 'notification_configs'
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(64), nullable=False) # email, wechat, feishu, webhook
    is_enabled = db.Column(db.Boolean, default=False)
    config_value = db.Column(db.String(256), nullable=True)

class SystemConfig(db.Model):
    __tablename__ = 'system_configs'
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(64), unique=True, nullable=False) # AGENT_AUTH_KEY, etc.
    config_value = db.Column(db.String(256), nullable=True)
