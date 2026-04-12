from flask import Blueprint, request, jsonify
from ..models import NotificationConfig, SystemConfig, db
from ..services.utils import token_required, log_audit
import requests
import smtplib
import ssl
import secrets
from email.mime.text import MIMEText
from datetime import datetime

settings = Blueprint('settings', __name__)


def _get_system_value(key: str, default_value: str = ''):
    cfg = SystemConfig.query.filter_by(config_key=key).first()
    return cfg.config_value if cfg else default_value


def _send_email_test(target_email: str, smtp_config: dict = None):
    smtp_config = smtp_config or {}

    smtp_server = (smtp_config.get('mail_server') or _get_system_value('MAIL_SERVER')).strip()
    smtp_port_raw = str(smtp_config.get('mail_port') or _get_system_value('MAIL_PORT', '465') or '465').strip()
    smtp_user = (smtp_config.get('mail_username') or _get_system_value('MAIL_USERNAME')).strip()
    smtp_pass = smtp_config.get('mail_password') or _get_system_value('MAIL_PASSWORD')
    smtp_encryption = (smtp_config.get('mail_encryption') or _get_system_value('MAIL_ENCRYPTION', 'SSL') or 'SSL').upper().strip()
    smtp_sender = (smtp_config.get('mail_default_sender') or _get_system_value('MAIL_DEFAULT_SENDER') or smtp_user).strip()

    if not smtp_server or not smtp_user or not smtp_pass or not target_email:
        raise ValueError('SMTP 配置不完整或目标邮箱为空')

    try:
        smtp_port = int(smtp_port_raw)
    except Exception:
        raise ValueError('SMTP 端口格式不正确')

    msg = MIMEText(
        f"TwinSentry 通知渠道测试成功。\n时间: {datetime.utcnow().isoformat()}Z",
        'plain',
        'utf-8'
    )
    msg['Subject'] = 'TwinSentry 通知测试'
    msg['From'] = smtp_sender
    msg['To'] = target_email

    if smtp_encryption == 'SSL':
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=10) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_sender, [target_email], msg.as_string())
    else:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            if smtp_encryption == 'STARTTLS':
                context = ssl.create_default_context()
                server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_sender, [target_email], msg.as_string())


def _send_webhook_test(url: str, channel: str):
    if not url:
        raise ValueError('Webhook 地址不能为空')

    now = datetime.utcnow().isoformat() + 'Z'
    if channel == 'wechat':
        payload = {
            'msgtype': 'text',
            'text': {'content': f'TwinSentry 企业微信通知测试成功，时间: {now}'}
        }
    elif channel == 'feishu':
        payload = {
            'msg_type': 'text',
            'content': {'text': f'TwinSentry 飞书通知测试成功，时间: {now}'}
        }
    else:
        payload = {
            'title': 'TwinSentry Notification Test',
            'text': f'TwinSentry {channel} 通知渠道测试成功，时间: {now}'
        }

    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code >= 400:
        raise ValueError(f'Webhook 响应异常: HTTP {resp.status_code}')

    if channel in ['wechat', 'feishu']:
        try:
            body = resp.json()
        except Exception:
            raise ValueError('Webhook 返回内容不是有效 JSON')

        if channel == 'wechat' and body.get('errcode', 0) != 0:
            raise ValueError(f"企业微信返回错误: {body.get('errmsg', body)}")

        if channel == 'feishu':
            feishu_code = body.get('code', body.get('StatusCode', 0))
            if feishu_code not in [0, '0', None]:
                raise ValueError(f"飞书返回错误: {body.get('msg', body.get('StatusMessage', body))}")

@settings.route('/notifications', methods=['GET', 'PUT'])
@token_required
def notification_settings(current_user):
    if request.method == 'GET':
        configs = NotificationConfig.query.all()
        # Initialize if empty
        if not configs:
            channels = ['email', 'wechat', 'feishu', 'webhook']
            for c in channels:
                db.session.add(NotificationConfig(channel=c))
            db.session.commit()
            configs = NotificationConfig.query.all()
            
        return jsonify([{
            'id': c.id,
            'channel': c.channel,
            'is_enabled': c.is_enabled,
            'config_value': c.config_value
        } for c in configs])

    data = request.get_json() # List of configs
    for item in data:
        cfg = NotificationConfig.query.get(item['id'])
        if cfg:
            cfg.is_enabled = item.get('is_enabled', cfg.is_enabled)
            cfg.config_value = item.get('config_value', cfg.config_value)
    
    db.session.commit()
    log_audit('修改通知配置', '成功', user_id=current_user.id, details=f"修改了 {len(data)} 项通知渠道配置")
    return jsonify({'message': 'Settings updated'})

@settings.route('/notifications/test', methods=['POST'])
@token_required
def test_notification_channel(current_user):
    data = request.get_json() or {}
    channel = (data.get('channel') or '').strip().lower()
    config_value = (data.get('config_value') or '').strip()

    if channel not in ['email', 'wechat', 'feishu', 'webhook']:
        return jsonify({'message': 'Unsupported channel'}), 400

    try:
        if channel == 'email':
            _send_email_test(config_value, data.get('smtp_config') or {})
        else:
            _send_webhook_test(config_value, channel)

        log_audit('测试通知渠道', '成功', user_id=current_user.id, details=f"渠道: {channel}, 目标: {config_value}")
        return jsonify({'message': f'{channel.upper()} 测试成功'})
    except Exception as e:
        log_audit('测试通知渠道', '失败', user_id=current_user.id, details=f"渠道: {channel}, 原因: {str(e)}")
        return jsonify({'message': f'{channel.upper()} 测试失败: {str(e)}'}), 400


@settings.route('/system', methods=['GET', 'PUT'])
@token_required
def system_settings(current_user):
    # Keys we want to handle
    target_keys = [
        'NOTIFY_TIMEOUT_MINUTES',
        'MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 
        'MAIL_PASSWORD', 'MAIL_ENCRYPTION', 'MAIL_DEFAULT_SENDER',
        'DEDUPLICATION_ENABLED', 'DEDUPLICATION_MODE',
        'ANALYSIS_AGENT_KEY', 'ACTION_AGENT_KEY'
    ]
    
    if request.method == 'GET':
        results = {}
        for key in target_keys:
            config = SystemConfig.query.filter_by(config_key=key).first()
            if config:
                val = config.config_value
                # Try to cast numeric for frontend convenience
                if key == 'NOTIFY_TIMEOUT_MINUTES' or key == 'MAIL_PORT':
                    try: val = int(val)
                    except: val = 0
                results[key.lower()] = val
            else:
                results[key.lower()] = ""
        return jsonify(results)

    data = request.get_json()
    for key in target_keys:
        json_key = key.lower()
        if json_key in data:
            val = str(data[json_key])
            config = SystemConfig.query.filter_by(config_key=key).first()
            if not config:
                config = SystemConfig(config_key=key, config_value=val)
                db.session.add(config)
            else:
                config.config_value = val
    
    db.session.commit()
    log_audit('修改系统配置', '成功', user_id=current_user.id, details="更新了系统全局参数")
    return jsonify({'message': 'System settings updated'})


@settings.route('/system/reset-agent-key', methods=['POST'])
@token_required
def reset_agent_key(current_user):
    data = request.get_json() or {}
    agent_type = (data.get('agent_type') or '').strip().lower()

    key_map = {
        'analysis': 'ANALYSIS_AGENT_KEY',
        'disposition': 'ACTION_AGENT_KEY'
    }

    if agent_type not in key_map:
        log_audit('重置Agent Key', '失败', user_id=current_user.id, details=f"非法类型: {agent_type}")
        return jsonify({'message': 'Invalid agent_type, expected analysis or disposition'}), 400

    config_key = key_map[agent_type]
    new_key = secrets.token_hex(16)

    config = SystemConfig.query.filter_by(config_key=config_key).first()
    if not config:
        config = SystemConfig(config_key=config_key, config_value=new_key)
        db.session.add(config)
    else:
        config.config_value = new_key

    db.session.commit()
    log_audit('重置Agent Key', '成功', user_id=current_user.id, details=f"{config_key} 已重置")

    return jsonify({
        'message': f'{agent_type} agent key reset successfully',
        'key_type': agent_type,
        'key_value': new_key
    })
