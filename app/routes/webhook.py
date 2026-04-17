from flask import Blueprint, request, jsonify
from ..models import Alert, db, AlertStatus, SystemConfig
from ..services.utils import log_audit, token_required
import json
import requests
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

webhook = Blueprint('webhook', __name__)


@webhook.route('/receiver', methods=['POST'])
def receive_alert():
    try:
        data = request.get_json()
        if not data or 'title' not in data or 'text' not in data:
            return jsonify({'message': 'Invalid data format, title and text required'}), 400

        title = data['title']
        raw_text = data['text']

        # Deduplication check
        dedup_enabled = SystemConfig.query.filter_by(config_key='DEDUPLICATION_ENABLED').first()
        if dedup_enabled and dedup_enabled.config_value.lower() == 'true':
            dedup_mode = SystemConfig.query.filter_by(config_key='DEDUPLICATION_MODE').first()
            mode = dedup_mode.config_value if dedup_mode else 'title'

            # Only check for PENDING alerts
            query = Alert.query.filter_by(status=AlertStatus.PENDING.value, is_delete=0)
            if mode == 'title':
                existing = query.filter_by(title=title).first()
            else: # title+content
                existing = query.filter_by(title=title, raw_text=raw_text).first()

            if existing:
                log_audit('数据接收', '触发去重', ip_address=request.remote_addr, details=f"标题：{title}")
                return jsonify({'message': 'Alert deduplicated', 'id': existing.id}), 200

        # 解析逻辑：将 \r, \n, \r\n 换成列表
        content_list = []
        if raw_text:
            # First replace \r\n with \n, then \r with \n, then split
            normalized_text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
            content_list = [line.strip() for line in normalized_text.split('\n') if line.strip()]

        new_alert = Alert(
            title=title,
            raw_text=raw_text,
            content=content_list,
            status=AlertStatus.PENDING.value
        )

        db.session.add(new_alert)
        db.session.commit()

        log_audit('数据接收', '成功', ip_address=request.remote_addr, details=f"新增告警 ID: {new_alert.id}, 标题：{title}")

        return jsonify({'message': 'Alert received', 'id': new_alert.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error processing webhook: {str(e)}'}), 500


@webhook.route('/forward-to-openclaw', methods=['POST'])
@token_required
def forward_to_openclaw(current_user):
    """外发安全事件到 OpenClaw 系统"""
    data = request.get_json() or {}
    alert_id = data.get('alert_id')
    target = data.get('target')  # 'analysis' or 'action'

    if not alert_id or not target:
        return jsonify({'message': 'alert_id 和 target 参数必填'}), 400

    if target not in ['analysis', 'action']:
        return jsonify({'message': 'target 参数必须是 analysis 或 action'}), 400

    # 获取告警（使用 alert_id 字段）
    alert = Alert.query.filter_by(alert_id=alert_id, is_delete=0).first()
    if not alert:
        return jsonify({'message': '告警不存在或已删除'}), 404

    # 状态检查 (使用数字状态值)
    if target == 'analysis' and alert.status != AlertStatus.PENDING.value:
        return jsonify({'message': '当前告警状态不支持外发至分析智能体'}), 400
    if target == 'action' and alert.status != AlertStatus.ANALYZED.value:
        return jsonify({'message': '当前告警状态不支持外发至处置智能体'}), 400

    # 获取 OpenClaw 配置
    base_url_cfg = SystemConfig.query.filter_by(config_key='OPENCLAW_BASE_URL').first()
    token_cfg = SystemConfig.query.filter_by(config_key='OPENCLAW_WEBHOOK_TOKEN').first()
    path_cfg = SystemConfig.query.filter_by(
        config_key='OPENCLAW_ANALYSIS_PATH' if target == 'analysis' else 'OPENCLAW_ACTION_PATH'
    ).first()

    base_url = base_url_cfg.config_value if base_url_cfg else ''
    webhook_token = token_cfg.config_value if token_cfg else ''
    hook_path = path_cfg.config_value if path_cfg else ''

    if not base_url or not webhook_token or not hook_path:
        log_audit('外发 OpenClaw', '失败', user_id=current_user.id,
                  details=f"告警 ID: {alert_id}, OpenClaw 配置不完整")
        return jsonify({'message': 'OpenClaw 配置不完整，请在 Agent 设置中配置'}), 400

    # 构建请求
    full_url = base_url.rstrip('/') + hook_path

    # 确定 agentId
    agent_id = 'eleanor' if target == 'analysis' else 'aria'

    # 获取本机 IP 作为 source
    import socket
    try:
        source_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        source_ip = '127.0.0.1'

    payload = {
        'agentId': agent_id,
        'alert_id': alert.alert_id,
        'source': source_ip
    }

    headers = {
        'Authorization': f'Bearer {webhook_token}',
        'Content-Type': 'application/json'
    }

    try:
        # 发送 POST 请求，忽略 SSL 证书验证（因为是内部系统）
        resp = requests.post(full_url, json=payload, headers=headers, timeout=10, verify=False)

        if resp.status_code >= 400:
            raise Exception(f'OpenClaw 返回错误：HTTP {resp.status_code}')

        log_audit('外发 OpenClaw', '成功', user_id=current_user.id,
                  details=f"告警 ID: {alert.alert_id}, 目标：{target}, agentId: {agent_id}, URL: {full_url}")

        # 更新告警状态
        if target == 'analysis':
            alert.status = AlertStatus.ANALYZING.value
        else:
            alert.status = AlertStatus.PROCESSING.value
        db.session.commit()

        # 解析 OpenClaw 响应
        try:
            openclaw_response = resp.json()
        except Exception:
            openclaw_response = {'raw': resp.text}

        return jsonify({
            'message': '外发成功',
            'data': {
                'alert_id': alert.alert_id,
                'target': target,
                'agent_id': agent_id,
                'url': full_url,
                'openclaw_response': openclaw_response
            }
        })

    except Exception as e:
        log_audit('外发 OpenClaw', '失败', user_id=current_user.id,
                  details=f"告警 ID: {alert.alert_id}, 原因：{str(e)}")
        return jsonify({'message': f'外发失败：{str(e)}'}), 500
