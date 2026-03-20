from flask import Blueprint, request
from datetime import datetime
from ..models import Alert, db, AlertStatus, SystemConfig
from ..services.utils import log_audit, api_response, verify_agent_key

agents = Blueprint('agents', __name__)


def _agent_auth_or_401(agent_type='ANALYSIS'):
    ok, reason = verify_agent_key(agent_type=agent_type, return_reason=True)
    if ok:
        return None

    action = '分析智能体认证失败' if agent_type == 'ANALYSIS' else '处置智能体认证失败'
    reason_map = {
        'missing_key': '缺少 Key',
        'invalid_key': '无效 Key',
    }
    log_audit(action, reason_map.get(reason, '认证失败'))

    msg = 'Unauthorized Analysis Agent' if agent_type == 'ANALYSIS' else 'Unauthorized Disposition Agent'
    return api_response(code=401, msg=msg), 401

@agents.route('/analysis/fetch', methods=['GET'])
def analysis_fetch():
    auth_error = _agent_auth_or_401(agent_type='ANALYSIS')
    if auth_error:
        return auth_error
    
    # Get latest PENDING alert with priority support and row-level locking
    alert = Alert.query.filter_by(status=AlertStatus.PENDING.value, is_delete=0) \
        .order_by(Alert.priority.asc(), Alert.created_at.asc()) \
        .with_for_update(skip_locked=True) \
        .first()
    
    if not alert:
        return api_response(code=404, msg='No pending alerts available'), 404
    
    # Update status to ANALYZING
    alert.status = AlertStatus.ANALYZING.value
    db.session.commit()
    
    log_audit('智能体拉取分析任务', '成功', details=f"告警 ID: {alert.id}, 标题: {alert.title}")
    
    return api_response(data={
        'alert': {
            'id': alert.id,
            'title': alert.title,
            'content': alert.content,
            'raw_text': alert.raw_text,
            'text_lines': alert.content, # For compatibility with fetch_task
            'created_at': alert.created_at.isoformat()
        }
    })

@agents.route('/analysis/submit', methods=['POST'])
def analysis_submit():
    auth_error = _agent_auth_or_401(agent_type='ANALYSIS')
    if auth_error:
        return auth_error
    
    data = request.get_json()
    alert_id = data.get('alert_id') or data.get('id')
    analysis_log = data.get('analysis_log') or data.get('result')
    enrichment_data = data.get('enrichment_data')
    
    if not alert_id or not analysis_log:
        return api_response(code=400, msg='ID and analysis_log required'), 400
    
    alert = Alert.query.filter_by(id=alert_id, is_delete=0).first()
    if not alert:
        return api_response(code=404, msg='Alert not found'), 404
    
    alert.analysis_result = analysis_log
    alert.analysis_time = datetime.utcnow()
    if enrichment_data:
        # Assuming we might want to store enrichment data separately or in a specific field
        # For now, let's just append or keep in a text field if models allow
        pass

    alert.status = AlertStatus.ANALYZED.value
    db.session.commit()
    
    log_audit('智能体提交分析结论', '成功', details=f"告警 ID: {alert.id}, 结论内容: {analysis_log[:200]}...")
    return api_response(msg='Analysis result submitted')

@agents.route('/process/fetch', methods=['GET'])
@agents.route('/disposition/fetch', methods=['GET'])
def process_fetch():
    auth_error = _agent_auth_or_401(agent_type='DISPOSITION')
    if auth_error:
        return auth_error
    
    # Get latest ANALYZED alert with priority support and row-level locking
    alert = Alert.query.filter_by(status=AlertStatus.ANALYZED.value, is_delete=0) \
        .order_by(Alert.priority.asc(), Alert.created_at.asc()) \
        .with_for_update(skip_locked=True) \
        .first()
    
    if not alert:
        return api_response(code=404, msg='No analyzed alerts available'), 404
    
    # Update status to PROCESSING
    alert.status = AlertStatus.PROCESSING.value
    db.session.commit()
    
    log_audit('智能体拉取处置任务', '成功', details=f"告警 ID: {alert.id}, 标题: {alert.title}")
    
    return api_response(data={
        'alert': {
            'id': alert.id,
            'title': alert.title,
            'content': alert.content,
            'raw_text': alert.raw_text,
            'analysis_log': alert.analysis_result,
            'created_at': alert.created_at.isoformat()
        }
    })

@agents.route('/process/submit', methods=['POST'])
@agents.route('/disposition/submit', methods=['POST'])
def process_submit():
    auth_error = _agent_auth_or_401(agent_type='DISPOSITION')
    if auth_error:
        return auth_error
    
    data = request.get_json()
    alert_id = data.get('alert_id') or data.get('id')
    action_log = data.get('action_log') or data.get('result')
    
    if not alert_id or not action_log:
        return api_response(code=400, msg='ID and result required'), 400
    
    alert = Alert.query.filter_by(id=alert_id, is_delete=0).first()
    if not alert:
        return api_response(code=404, msg='Alert not found'), 404
    
    alert.process_result = action_log
    alert.process_time = datetime.utcnow()
    alert.status = AlertStatus.PROCESSED.value
    db.session.commit()
    
    log_audit('智能体提交处置结论', '成功', details=f"告警 ID: {alert.id}, 处置内容: {action_log[:200]}...")
    return api_response(msg='Process result submitted')

@agents.route('/config/key', methods=['GET'])
def get_key():
    analysis_config = SystemConfig.query.filter_by(config_key='ANALYSIS_AGENT_KEY').first()
    disposition_config = SystemConfig.query.filter_by(config_key='DISPOSITION_AGENT_KEY').first()
    return api_response(data={
        'analysis_agent_key': analysis_config.config_value if analysis_config else "NOT_FOUND",
        'disposition_agent_key': disposition_config.config_value if disposition_config else "NOT_FOUND"
    })
