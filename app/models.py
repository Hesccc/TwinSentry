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


# ==============================================================================
# Agent Engine & Workflow Data Models
# ==============================================================================

class PromptTemplate(db.Model):
    """提示词模板表"""
    __tablename__ = 'prompt_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    agent_code = db.Column(db.String(64), nullable=False)  # supervisor, analysis, action, etc.
    system_prompt = db.Column(db.Text, nullable=False)
    user_template = db.Column(db.Text, nullable=True)      # 支持 {{alert.text}} 插值
    version = db.Column(db.Integer, default=1)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'agent_code': self.agent_code,
            'system_prompt': self.system_prompt,
            'user_template': self.user_template,
            'version': self.version,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ToolDefinition(db.Model):
    """工具与 MCP 协议注册表"""
    __tablename__ = 'tool_definitions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    code = db.Column(db.String(64), unique=True, nullable=False)
    tool_type = db.Column(db.String(32), nullable=False)   # mcp_stdio, mcp_sse, python_skill
    description = db.Column(db.Text, nullable=True)
    config = db.Column(db.JSON, nullable=True)             # mcp 命令、参数或 url
    parameters_schema = db.Column(db.JSON, nullable=True)  # 函数入参 schema
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'tool_type': self.tool_type,
            'description': self.description,
            'config': self.config,
            'parameters_schema': self.parameters_schema,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AgentDefinition(db.Model):
    """智能体定义表"""
    __tablename__ = 'agent_definitions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    code = db.Column(db.String(64), unique=True, nullable=False)
    role = db.Column(db.String(64), default='analyst')      # supervisor, analyst, responder, general
    model_provider = db.Column(db.String(64), default='openai') # openai, deepseek, qwen, ollama
    model_name = db.Column(db.String(64), default='gpt-4o-mini')
    temperature = db.Column(db.Float, default=0.2)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompt_templates.id'), nullable=True)
    tools_config = db.Column(db.JSON, default=list)        # 挂载的 tool_code 数组
    sub_agents = db.Column(db.JSON, default=list)          # 子 Agent code 列表
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prompt = db.relationship('PromptTemplate', backref='agents')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'role': self.role,
            'model_provider': self.model_provider,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'prompt_id': self.prompt_id,
            'prompt': self.prompt.to_dict() if self.prompt else None,
            'tools_config': self.tools_config or [],
            'sub_agents': self.sub_agents or [],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WorkflowDefinition(db.Model):
    """多 Agent 连线编排工作流定义表"""
    __tablename__ = 'workflow_definitions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    graph_data = db.Column(db.JSON, nullable=False)        # React Flow 的 nodes 与 edges
    is_active = db.Column(db.Boolean, default=False)       # 是否设为默认告警响应工作流
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'graph_data': self.graph_data,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WorkflowExecution(db.Model):
    """工作流运行执行实例与日志记录"""
    __tablename__ = 'workflow_executions'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow_definitions.id'), nullable=True)
    alert_id = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default='running')    # running, completed, failed
    execution_steps = db.Column(db.JSON, default=list)     # 各节点执行轨迹、输入与输出
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'alert_id': self.alert_id,
            'status': self.status,
            'execution_steps': self.execution_steps or [],
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None
        }





class GoldenSOP(db.Model):
    """人工校准沉淀的黄金 SOP 知识库 (知识飞轮)"""
    __tablename__ = 'golden_sops'
    id = db.Column(db.Integer, primary_key=True)
    alert_pattern = db.Column(db.String(128), nullable=False)   # 告警指纹/类型
    title = db.Column(db.String(256), nullable=False)
    sop_content = db.Column(db.Text, nullable=False)            # Markdown 格式的权威 SOP
    calibrated_by = db.Column(db.String(64), default='admin')
    use_count = db.Column(db.Integer, default=1)                # 命中复用次数
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'alert_pattern': self.alert_pattern,
            'title': self.title,
            'sop_content': self.sop_content,
            'calibrated_by': self.calibrated_by,
            'use_count': self.use_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AlertSOPRecord(db.Model):
    """当前告警的排障工作台 SOP 实例记录 (包含证据链与人工修正)"""
    __tablename__ = 'alert_sop_records'
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.String(64), nullable=False)
    target_index = db.Column(db.String(64), nullable=True)     # Splunk 锁定索引
    splunk_evidence = db.Column(db.JSON, default=list)         # Splunk 原始证据链日志
    rca_summary = db.Column(db.Text, nullable=True)            # 根因结论
    verifier_report = db.Column(db.JSON, nullable=True)        # 质检结果
    sop_content = db.Column(db.Text, nullable=False)           # 动态 SOP (支持人工实时修改)
    status = db.Column(db.String(32), default='draft')         # draft (草稿/待确认), confirmed (已确认执行)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'target_index': self.target_index,
            'splunk_evidence': self.splunk_evidence or [],
            'rca_summary': self.rca_summary,
            'verifier_report': self.verifier_report or {},
            'sop_content': self.sop_content,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

