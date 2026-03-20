from flask import Blueprint, request, jsonify
from ..models import Alert, db, AlertStatus, SystemConfig
from ..services.utils import log_audit
import json

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
                log_audit('数据接收', '触发去重', ip_address=request.remote_addr, details=f"标题: {title}")
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
        
        log_audit('数据接收', '成功', ip_address=request.remote_addr, details=f"新增告警 ID: {new_alert.id}, 标题: {title}")
        
        return jsonify({'message': 'Alert received', 'id': new_alert.id}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error processing webhook: {str(e)}'}), 500
