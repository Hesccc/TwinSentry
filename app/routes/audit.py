from flask import Blueprint, jsonify
from ..models import AuditLog, db
from ..services.utils import token_required
from sqlalchemy import func
from datetime import datetime, timedelta

audit = Blueprint('audit', __name__)

@audit.route('/stats', methods=['GET'])
@token_required
def audit_stats(current_user):
    # Return statistics grouped by hour for the last 24 hours
    last_24h = datetime.utcnow() - timedelta(hours=24)

    stats = db.session.query(
        func.date_trunc('hour', AuditLog.timestamp).label('hour'),
        AuditLog.action,
        func.count(AuditLog.id)
    ).filter(AuditLog.timestamp >= last_24h).group_by(func.date_trunc('hour', AuditLog.timestamp), AuditLog.action).all()

    agent_login_fail_stats = db.session.query(
        func.date_trunc('hour', AuditLog.timestamp).label('hour'),
        func.count(AuditLog.id)
    ).filter(
        AuditLog.timestamp >= last_24h,
        AuditLog.action.in_(['分析智能体认证失败', '处置智能体认证失败'])
    ).group_by(func.date_trunc('hour', AuditLog.timestamp)).all()

    return jsonify({
        'actions': [
            {'hour': str(s[0]), 'action': s[1], 'count': s[2]} for s in stats
        ],
        'agent_login_failures': [
            {'hour': str(s[0]), 'count': s[1]} for s in agent_login_fail_stats
        ]
    })

@audit.route('/logs', methods=['GET'])
@token_required
def audit_logs(current_user):
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': l.id,
        'user_id': l.user_id,
        'action': l.action,
        'status': l.status,
        'details': l.details,
        'ip_address': l.ip_address,
        'timestamp': l.timestamp.isoformat() + 'Z'
    } for l in logs])
