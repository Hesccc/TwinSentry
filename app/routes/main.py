from flask import Blueprint, request, jsonify, render_template
from ..models import Alert, AuditLog, db, AlertStatus
from ..services.utils import token_required, token_required_page, log_audit
from datetime import datetime, timedelta
from sqlalchemy import func, text

main = Blueprint('main', __name__)

@main.route('/login')
def login_page():
    return render_template('login.html')

@main.route('/')
@token_required_page
def index():
    return render_template('dashboard.html')

@main.route('/alerts')
@token_required_page
def alerts_page():
    return render_template('alerts.html')

@main.route('/settings')
@token_required_page
def settings_page():
    return render_template('settings.html')

@main.route('/audit')
@token_required_page
def audit_page():
    return render_template('audit.html')

@main.route('/profile')
@token_required_page
def profile_page():
    return render_template('profile.html')

@main.route('/api-docs-page')
@token_required_page
def docs_page():
    return render_template('docs.html')

@main.route('/skills-page')
@token_required_page
def skills_page():
    return render_template('skills.html')

@main.route('/api/alerts', methods=['GET'])
@token_required
def get_alerts(current_user):
    alerts = Alert.query.filter_by(is_delete=0).order_by(Alert.id.asc()).all()
    return jsonify([{
        'id': a.id,
        'title': a.title,
        'content': a.content,
        'raw_text': a.raw_text,
        'status': a.status,
        'analysis_result': a.analysis_result,
        'process_result': a.process_result,
        'analysis_time': a.analysis_time.isoformat() + 'Z' if a.analysis_time else None,
        'process_time': a.process_time.isoformat() + 'Z' if a.process_time else None,
        'created_at': a.created_at.isoformat() + 'Z',
        'updated_at': a.updated_at.isoformat() + 'Z'
    } for a in alerts])

@main.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
@token_required
def delete_alert(current_user, alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_delete = 1
    db.session.commit()
    return jsonify({'message': 'Alert marked as deleted'})

@main.route('/api/alerts/<int:alert_id>/rollback', methods=['POST'])
@token_required
def rollback_alert_status(current_user, alert_id):
    alert = Alert.query.filter_by(id=alert_id, is_delete=0).first()
    if not alert:
        log_audit('人工回退告警状态', '失败', user_id=current_user.id, details=f"告警不存在或已删除，ID: {alert_id}")
        return jsonify({'message': 'Alert not found'}), 404

    rollback_map = {
        AlertStatus.ANALYZING.value: AlertStatus.PENDING.value,
        AlertStatus.PROCESSING.value: AlertStatus.ANALYZED.value
    }

    target_status = rollback_map.get(alert.status)
    if not target_status:
        log_audit(
            '人工回退告警状态',
            '失败',
            user_id=current_user.id,
            details=f"告警 ID: {alert.id}, 标题: {alert.title}, 当前状态不支持回退: {alert.status}"
        )
        return jsonify({'message': 'Current status does not support rollback'}), 400

    from_status = alert.status
    alert.status = target_status
    db.session.commit()

    log_audit(
        '人工回退告警状态',
        '成功',
        user_id=current_user.id,
        details=f"告警 ID: {alert.id}, 标题: {alert.title}, 状态回退: {from_status} -> {target_status}"
    )

    return jsonify({
        'message': 'Rollback success',
        'data': {
            'id': alert.id,
            'from_status': from_status,
            'to_status': target_status
        }
    })

@main.route('/api/stats/dashboard', methods=['GET'])
@token_required
def dashboard_stats(current_user):
    # Status Distribution (Pie Chart)
    status_counts = db.session.query(
        Alert.status, func.count(Alert.id)
    ).filter(Alert.is_delete == 0).group_by(Alert.status).all()
    
    status_map = {s[0]: s[1] for s in status_counts}
    
    # Periodic trends (Last 24 hours)
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    
    # 1. Total Raw Trends (including deleted)
    raw_trends = db.session.query(
        func.date_trunc('hour', Alert.created_at).label('hour'),
        func.count(Alert.id)
    ).filter(Alert.created_at >= last_24h).group_by(func.date_trunc('hour', Alert.created_at)).all()
    
    # 2. Active Trends (not deleted)
    active_trends = db.session.query(
        func.date_trunc('hour', Alert.created_at).label('hour'),
        func.count(Alert.id)
    ).filter(
        Alert.created_at >= last_24h,
        Alert.is_delete == 0
    ).group_by(func.date_trunc('hour', Alert.created_at)).all()
    
    # 3. Processed Trends (status = 已处置)
    processed_trends = db.session.query(
        func.date_trunc('hour', Alert.updated_at).label('hour'),
        func.count(Alert.id)
    ).filter(
        Alert.status == AlertStatus.PROCESSED.value,
        Alert.updated_at >= last_24h
    ).group_by(func.date_trunc('hour', Alert.updated_at)).all()

    # 4. Deduplication Stats (from AuditLog)
    # DATA_INPUT with status 'Deduplicated' vs 'Success'
    dedup_count = db.session.query(func.count(AuditLog.id)).filter(
        AuditLog.action == 'DATA_INPUT',
        AuditLog.status == 'Deduplicated'
    ).scalar() or 0
    
    success_input = db.session.query(func.count(AuditLog.id)).filter(
        AuditLog.action == 'DATA_INPUT',
        AuditLog.status == 'Success'
    ).scalar() or 0

    # 5. Top 5 Alert Titles
    top_titles_query = db.session.query(
        Alert.title, func.count(Alert.id)
    ).filter(Alert.is_delete == 0).group_by(Alert.title).order_by(func.count(Alert.id).desc()).limit(5).all()
    top_titles = [{'title': t[0], 'count': t[1]} for t in top_titles_query]

    # 6. Recent Alerts (Activity Feed)
    recent_alerts_query = Alert.query.filter(Alert.is_delete == 0).order_by(Alert.created_at.desc()).limit(5).all()
    recent_alerts = [{
        'id': a.id,
        'title': a.title,
        'status': a.status,
        'time': a.created_at.isoformat() + 'Z'
    } for a in recent_alerts_query]

    # Supplementary Counts for Stat Cards
    total_raw = db.session.query(func.count(Alert.id)).scalar()
    total_active = db.session.query(func.count(Alert.id)).filter(Alert.is_delete == 0).scalar()
    total_pending = db.session.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.PENDING.value, Alert.is_delete == 0).scalar()
    total_processing = db.session.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.PROCESSING.value, Alert.is_delete == 0).scalar()
    total_processed = db.session.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.PROCESSED.value, Alert.is_delete == 0).scalar()

    return jsonify({
        'status_distribution': status_map,
        'raw_trends': [{'hour': str(h), 'count': c} for h, c in raw_trends],
        'active_trends': [{'hour': str(h), 'count': c} for h, c in active_trends],
        'processed_trends': [{'hour': str(h), 'count': c} for h, c in processed_trends],
        'dedup_stats': {
            'deduplicated': dedup_count,
            'ingested': success_input,
            'total_hits': dedup_count + success_input
        },
        'top_titles': top_titles,
        'recent_alerts': recent_alerts,
        'counts': {
            'total_raw': total_raw,
            'total_active': total_active,
            'total_pending': total_pending,
            'total_processing': total_processing,
            'total_processed': total_processed
        }
    })

@main.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({'status': 'online', 'timestamp': datetime.utcnow().isoformat() + 'Z'})

@main.route('/api/health', methods=['GET'])
def get_health():
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'database': str(e)}), 500
