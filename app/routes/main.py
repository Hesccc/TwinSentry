from flask import Blueprint, request, jsonify, render_template
from ..models import Alert, AuditLog, db, AlertStatus
from ..services.utils import token_required, token_required_page, log_audit
from datetime import datetime, timedelta
from sqlalchemy import func, text
import uuid

main = Blueprint('main', __name__)


# ==============================================================================
# 复合排序常量：解决同毫秒并发导致的分页数据丢失/重复问题
# 排序规则：created_at ASC (主排序) + alert_id ASC (决胜字段/Tie-breaker)
# ==============================================================================
ALERT_LIST_ORDER = [Alert.created_at.asc(), Alert.alert_id.asc()]


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


@main.route('/agent')
@token_required_page
def agent_settings_page():
    return render_template('agent.html')


@main.route('/skills-page')
@token_required_page
def skills_page():
    from flask import current_app
    import os

    skills_root = os.path.abspath(os.path.join(current_app.root_path, '..', 'skills'))
    available_skills = []

    if os.path.exists(skills_root):
        for item in os.listdir(skills_root):
            if os.path.isdir(os.path.join(skills_root, item)):
                available_skills.append({
                    'name': item,
                    'description': f"Agent Skill Package for {item}"
                })

    return render_template('skills.html', available_skills=available_skills)


@main.route('/api/alerts', methods=['GET'])
@token_required
def get_alerts(current_user):
    """
    获取告警列表（全量）
    排序：created_at ASC, alert_id ASC (复合排序，防止分页重复/丢失)
    """
    alerts = Alert.query.filter_by(is_delete=0).order_by(*ALERT_LIST_ORDER).all()
    return jsonify([a.to_dict() for a in alerts])


@main.route('/api/alerts/paginated', methods=['GET'])
@token_required
def get_alerts_paginated(current_user):
    """
    获取告警列表（分页查询）

    Query Parameters:
        - page: 页码 (默认 1)
        - per_page: 每页数量 (默认 20, 最大 100)
        - status: 状态筛选 (可选)
        - title: 标题模糊搜索 (可选)
        - start_date: 开始时间 ISO8601 (可选)
        - end_date: 结束时间 ISO8601 (可选)

    Response:
        {
            "items": [...],
            "total": 100,
            "page": 1,
            "per_page": 20,
            "pages": 5
        }

    排序：created_at ASC, alert_id ASC (复合排序，防止分页重复/丢失)
    """
    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # 限制最大每页数量

    # 构建查询
    query = Alert.query.filter_by(is_delete=0)

    # 状态筛选
    status = request.args.get('status', '').strip()
    if status:
        query = query.filter_by(status=status)

    # 标题模糊搜索
    title = request.args.get('title', '').strip()
    if title:
        query = query.filter(Alert.title.ilike(f'%{title}%'))

    # 时间范围筛选
    start_date = request.args.get('start_date', '').strip()
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Alert.created_at >= start_dt)
        except ValueError:
            pass

    end_date = request.args.get('end_date', '').strip()
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Alert.created_at <= end_dt)
        except ValueError:
            pass

    # 获取总数
    total = query.count()

    # 分页查询（强制使用复合排序）
    alerts = query.order_by(*ALERT_LIST_ORDER).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'items': [a.to_dict() for a in alerts],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })


@main.route('/api/alerts/<alert_id>', methods=['GET'])
@token_required
def get_alert(current_user, alert_id):
    """
    获取单个告警详情

    Path Parameters:
        - alert_id: 告警 UUID
    """
    alert = Alert.query.filter_by(alert_id=alert_id, is_delete=0).first()
    if not alert:
        return jsonify({'message': 'Alert not found'}), 404
    return jsonify(alert.to_dict())


@main.route('/api/alerts/<alert_id>', methods=['DELETE'])
@token_required
def delete_alert(current_user, alert_id):
    """
    删除告警（软删除）

    Path Parameters:
        - alert_id: 告警 UUID
    """
    alert = Alert.query.filter_by(alert_id=alert_id, is_delete=0).first()
    if not alert:
        return jsonify({'message': 'Alert not found'}), 404

    alert.is_delete = 1
    db.session.commit()

    log_audit('删除告警', '成功', user_id=current_user.id,
              details=f"告警 ID: {alert_id}, 标题：{alert.title}")

    return jsonify({'message': 'Alert marked as deleted'})


@main.route('/api/alerts/<alert_id>/rollback', methods=['POST'])
@token_required
def rollback_alert_status(current_user, alert_id):
    """
    回退告警状态

    Path Parameters:
        - alert_id: 告警 UUID

    支持的回退:
        - 分析中 -> 待分析
        - 处置中 -> 已分析
    """
    alert = Alert.query.filter_by(alert_id=alert_id, is_delete=0).first()
    if not alert:
        log_audit('人工回退告警状态', '失败', user_id=current_user.id,
                  details=f"告警不存在或已删除，ID: {alert_id}")
        return jsonify({'message': 'Alert not found'}), 404

    rollback_map = {
        AlertStatus.ANALYZING.value: AlertStatus.PENDING.value,
        AlertStatus.PROCESSING.value: AlertStatus.ANALYZED.value
    }

    target_status = rollback_map.get(alert.status)
    if not target_status:
        log_audit('人工回退告警状态', '失败', user_id=current_user.id,
                  details=f"告警 ID: {alert.alert_id}, 标题：{alert.title}, 当前状态不支持回退：{alert.status}")
        return jsonify({'message': 'Current status does not support rollback'}), 400

    from_status = alert.status
    alert.status = target_status
    db.session.commit()

    log_audit('人工回退告警状态', '成功', user_id=current_user.id,
              details=f"告警 ID: {alert.alert_id}, 标题：{alert.title}, 状态回退：{from_status} -> {target_status}")

    return jsonify({
        'message': 'Rollback success',
        'data': {
            'alert_id': alert.alert_id,
            'from_status': from_status,
            'to_status': target_status
        }
    })


@main.route('/api/alerts/<alert_id>/forward', methods=['POST'])
@token_required
def forward_alert(current_user, alert_id):
    """
    外发告警到 OpenClaw

    Path Parameters:
        - alert_id: 告警 UUID

    Request Body:
        - target: 'analysis' 或 'action'
    """
    # 此路由保留作为备份，主要功能在 webhook.py 中实现
    from .webhook import forward_to_openclaw
    return forward_to_openclaw(current_user)


@main.route('/api/stats/dashboard', methods=['GET'])
@token_required
def dashboard_stats(current_user):
    """
    获取仪表盘统计数据

    排序规则：
        - 时间趋势：created_at ASC
        - 最新告警：created_at DESC, alert_id DESC
    """
    # Status Distribution (Pie Chart)
    status_counts = db.session.query(
        Alert.status, func.count(Alert.alert_id)
    ).filter(Alert.is_delete == 0).group_by(Alert.status).all()

    # Convert numeric status to Chinese labels for frontend display
    status_map = {AlertStatus.get_label(s[0]): s[1] for s in status_counts}

    # Periodic trends (Last 24 hours)
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)

    # 1. Total Raw Trends (including deleted)
    raw_trends = db.session.query(
        func.date_trunc('hour', Alert.created_at).label('hour'),
        func.count(Alert.alert_id)
    ).filter(Alert.created_at >= last_24h).group_by(func.date_trunc('hour', Alert.created_at)).all()

    # 2. Active Trends (not deleted)
    active_trends = db.session.query(
        func.date_trunc('hour', Alert.created_at).label('hour'),
        func.count(Alert.alert_id)
    ).filter(
        Alert.created_at >= last_24h,
        Alert.is_delete == 0
    ).group_by(func.date_trunc('hour', Alert.created_at)).all()

    # 3. Processed Trends (status = 已处置)
    processed_trends = db.session.query(
        func.date_trunc('hour', Alert.updated_at).label('hour'),
        func.count(Alert.alert_id)
    ).filter(
        Alert.status == AlertStatus.PROCESSED.value,
        Alert.updated_at >= last_24h
    ).group_by(func.date_trunc('hour', Alert.updated_at)).all()

    # 4. Deduplication Stats (from AuditLog)
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
        Alert.title, func.count(Alert.alert_id)
    ).filter(Alert.is_delete == 0).group_by(Alert.title).order_by(func.count(Alert.alert_id).desc()).limit(5).all()
    top_titles = [{'title': t[0], 'count': t[1]} for t in top_titles_query]

    # 6. Recent Alerts (Activity Feed) - 使用复合排序
    recent_alerts_query = Alert.query.filter(Alert.is_delete == 0)\
        .order_by(Alert.created_at.desc(), Alert.alert_id.desc()).limit(5).all()
    recent_alerts = [{
        'alert_id': a.alert_id,
        'id': a.alert_id,  # 兼容旧字段
        'title': a.title,
        'status': a.status,
        'status_label': a.status_label,
        'time': a.created_at.isoformat() + 'Z'
    } for a in recent_alerts_query]

    # Supplementary Counts for Stat Cards
    total_raw = db.session.query(func.count(Alert.alert_id)).scalar()
    total_active = db.session.query(func.count(Alert.alert_id)).filter(Alert.is_delete == 0).scalar()
    total_pending = db.session.query(func.count(Alert.alert_id)).filter(
        Alert.status == AlertStatus.PENDING.value, Alert.is_delete == 0).scalar()
    total_processing = db.session.query(func.count(Alert.alert_id)).filter(
        Alert.status == AlertStatus.PROCESSING.value, Alert.is_delete == 0).scalar()
    total_processed = db.session.query(func.count(Alert.alert_id)).filter(
        Alert.status == AlertStatus.PROCESSED.value, Alert.is_delete == 0).scalar()

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
