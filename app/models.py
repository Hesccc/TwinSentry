from datetime import datetime
from . import db, bcrypt
import enum
import uuid

class AlertStatus(enum.Enum):
    """告警状态枚举 (数字字典)"""
    PENDING = 1     # 待分析
    ANALYZING = 2   # 分析中
    ANALYZED = 3    # 已分析
    PROCESSING = 4  # 处置中
    PROCESSED = 5   # 已处置

    @classmethod
    def get_label(cls, value):
        """根据状态值获取中文标签"""
        # Convert string to int if needed
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                return '未知'
        label_map = {
            1: '待分析',
            2: '分析中',
            3: '已分析',
            4: '处置中',
            5: '已处置'
        }
        return label_map.get(value, '未知')

    @classmethod
    def from_label(cls, label):
        """根据中文标签获取状态值"""
        label_map = {
            '待分析': 1,
            '分析中': 2,
            '已分析': 3,
            '处置中': 4,
            '已处置': 5
        }
        return label_map.get(label)

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

    # UUID 主键 - 防猜测
    alert_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.JSON, nullable=False)  # Parsed list from \r\n
    raw_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.Integer, default=AlertStatus.PENDING.value)  # 1:待分析，2:分析中，3:已分析，4:处置中，5:已处置
    analysis_result = db.Column(db.Text, nullable=True)
    process_result = db.Column(db.Text, nullable=True)
    analysis_time = db.Column(db.DateTime, nullable=True)
    process_time = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.Integer, default=2)  # 1: High, 2: Medium, 3: Low
    is_delete = db.Column(db.Integer, default=0)  # 0: False, 1: True

    # TIMESTAMP 类型，数据库层面默认值 CURRENT_TIMESTAMP，索引字段
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def status_label(self):
        """获取状态中文标签"""
        return AlertStatus.get_label(self.status)

    def to_dict(self):
        """转换为字典（用于 API 响应）"""
        return {
            'alert_id': self.alert_id,
            'id': self.alert_id,  # 兼容旧字段名
            'title': self.title,
            'content': self.content,
            'raw_text': self.raw_text,
            'status': self.status,
            'status_label': self.status_label,  # 中文标签
            'analysis_result': self.analysis_result,
            'process_result': self.process_result,
            'analysis_time': self.analysis_time.isoformat() + 'Z' if self.analysis_time else None,
            'process_time': self.process_time.isoformat() + 'Z' if self.process_time else None,
            'priority': self.priority,
            'is_delete': self.is_delete,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False)  # LOGIN, AGENT_FETCH_DATA, DATA_INPUT
    status = db.Column(db.String(32), nullable=False)  # Success, Failed
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class NotificationConfig(db.Model):
    __tablename__ = 'notification_configs'
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(64), nullable=False)  # email, wechat, feishu, webhook
    is_enabled = db.Column(db.Boolean, default=False)
    config_value = db.Column(db.String(256), nullable=True)

class SystemConfig(db.Model):
    __tablename__ = 'system_configs'
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(64), unique=True, nullable=False)  # AGENT_AUTH_KEY, etc.
    config_value = db.Column(db.String(256), nullable=True)
