from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_apscheduler import APScheduler
from flask_cors import CORS
from config import config

db = SQLAlchemy()
bcrypt = Bcrypt()
import os
scheduler = APScheduler()

def create_app(config_name='default'):
    # Fix for psycopg2 UnicodeDecodeError on Windows with non-ASCII paths
    os.environ['PGCLIENTENCODING'] = 'utf8'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    CORS(app)
    
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
    
    # Register blueprints
    from .routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
    
    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from .routes.agents import agents as agents_blueprint
    app.register_blueprint(agents_blueprint)
    
    from .routes.webhook import webhook as webhook_blueprint
    app.register_blueprint(webhook_blueprint, url_prefix='/api/webhook')

    from .routes.audit import audit as audit_blueprint
    app.register_blueprint(audit_blueprint, url_prefix='/api/audit')

    from .routes.settings import settings as settings_blueprint
    app.register_blueprint(settings_blueprint, url_prefix='/api/settings')

    from .routes.docs import docs as docs_blueprint
    app.register_blueprint(docs_blueprint)

    # Add scheduler jobs
    from .services.notifications import check_timeouts
    if not scheduler.get_job('timeout_check'):
        scheduler.add_job(id='timeout_check', func=check_timeouts, trigger='interval', minutes=20)

    # Initial Data Setup
    def setup_initial_data(application):
        with application.app_context():
            from .models import User, SystemConfig, NotificationConfig
            db.create_all()
            
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', email='admin@twinsentry.local')
                admin.set_password('admin@123')
                db.session.add(admin)
            
            if not SystemConfig.query.filter_by(config_key='ANALYSIS_AGENT_KEY').first():
                import secrets
                db.session.add(SystemConfig(config_key='ANALYSIS_AGENT_KEY', config_value=secrets.token_hex(16)))
            
            if not SystemConfig.query.filter_by(config_key='DISPOSITION_AGENT_KEY').first():
                import secrets
                db.session.add(SystemConfig(config_key='DISPOSITION_AGENT_KEY', config_value=secrets.token_hex(16)))
            
            if not SystemConfig.query.filter_by(config_key='NOTIFY_TIMEOUT_MINUTES').first():
                db.session.add(SystemConfig(config_key='NOTIFY_TIMEOUT_MINUTES', config_value='20'))
            
            # SMTP Defaults
            smtp_defaults = {
                'MAIL_SERVER': 'smtp.example.com',
                'MAIL_PORT': '465',
                'MAIL_USERNAME': '',
                'MAIL_PASSWORD': '',
                'MAIL_ENCRYPTION': 'SSL',
                'MAIL_DEFAULT_SENDER': 'twinsentry@example.com'
            }
            for k, v in smtp_defaults.items():
                if not SystemConfig.query.filter_by(config_key=k).first():
                    db.session.add(SystemConfig(config_key=k, config_value=v))
                
            if not NotificationConfig.query.all():
                for c in ['email', 'wechat', 'feishu', 'webhook']:
                    db.session.add(NotificationConfig(channel=c))
            
            # Deduplication Defaults
            if not SystemConfig.query.filter_by(config_key='DEDUPLICATION_ENABLED').first():
                db.session.add(SystemConfig(config_key='DEDUPLICATION_ENABLED', config_value='false'))
            if not SystemConfig.query.filter_by(config_key='DEDUPLICATION_MODE').first():
                db.session.add(SystemConfig(config_key='DEDUPLICATION_MODE', config_value='title'))
            
            # Mock Alert Data
            from .models import Alert, AlertStatus
            if not Alert.query.first():
                mocks = [
                    Alert(
                        title="[严重] 核心数据库连接超时",
                        raw_text="Service: Order-DB\nStatus: Timeout\nLatency: 5200ms\nMessage: Connection pool exhausted",
                        content=["Service: Order-DB", "Status: Timeout", "Latency: 5200ms"],
                        status=AlertStatus.PENDING.value,
                        priority=1 # High
                    ),
                    Alert(
                        title="[警告] API网关CPU负载过高",
                        raw_text="Host: web-gateway-01\nLoad: 95%\nThreshold: 80%",
                        content=["Host: web-gateway-01", "Load: 95%", "Threshold: 80%"],
                        status=AlertStatus.PENDING.value,
                        priority=2 # Medium
                    ),
                    Alert(
                        title="[通知] 关键系统配置文件变更",
                        raw_text="User: admin\nFile: /etc/nginx/conf.d/api.conf\nAction: Modified",
                        content=["User: admin", "File: api.conf", "Action: Modified"],
                        status=AlertStatus.PENDING.value,
                        priority=3 # Low
                    )
                ]
                db.session.add_all(mocks)
                print("Database seeded with mock alerts.")

            db.session.commit()
    
    setup_initial_data(app)

    return app
