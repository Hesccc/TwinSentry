from .. import db, scheduler
from ..models import Alert, AlertStatus, NotificationConfig
from datetime import datetime, timedelta
import requests

def send_notification(channel, message):
    # This is a mockup for different channels
    print(f"Sending {channel} notification: {message}")
    # Implementation for email, wechat, etc. would go here

def check_timeouts():
    with scheduler.app.app_context():
        from ..models import SystemConfig
        # Check timeout config
        timeout_cfg = SystemConfig.query.filter_by(config_key='NOTIFY_TIMEOUT_MINUTES').first()
        timeout_mins = int(timeout_cfg.config_value) if timeout_cfg else 20
        
        # Check alerts older than timeout_mins in non-final states
        timeout_limit = datetime.utcnow() - timedelta(minutes=timeout_mins)
        pending_alerts = Alert.query.filter(
            Alert.status.in_([
                AlertStatus.PENDING.value, 
                AlertStatus.ANALYZING.value, 
                AlertStatus.ANALYZED.value, 
                AlertStatus.PROCESSING.value
            ]),
            Alert.created_at <= timeout_limit,
            Alert.is_delete == 0
        ).all()
        
        if pending_alerts:
            msg = f"Timeout Alert Notification: {len(pending_alerts)} alerts are pending processing for over 20 minutes."
            enabled_configs = NotificationConfig.query.filter_by(is_enabled=True).all()
            for config in enabled_configs:
                send_notification(config.channel, msg)

# Schedule the task in app/__init__.py transition
# scheduler.add_job(id='timeout_check', func=check_timeouts, trigger='interval', minutes=20)
