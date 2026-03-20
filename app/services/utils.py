import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, redirect
from ..models import User

def api_response(code=0, msg="success", data=None):
    return jsonify({
        "code": code,
        "msg": msg,
        "data": data or {}
    })

def verify_agent_key(agent_type='ANALYSIS', return_reason=False):
    from .. import db
    from ..models import SystemConfig
    import secrets

    # Map agent type to config key
    config_key = 'ANALYSIS_AGENT_KEY' if agent_type == 'ANALYSIS' else 'DISPOSITION_AGENT_KEY'

    # Try header first, then query parameter
    auth_header = request.headers.get('X-Agent-Key')
    api_key_param = request.args.get('api_key')

    auth_key = auth_header or api_key_param

    if not auth_key:
        return (False, 'missing_key') if return_reason else False

    config = SystemConfig.query.filter_by(config_key=config_key).first()
    if not config:
        # Initialize key if not exists (fallback or during first migration)
        new_key = secrets.token_hex(16)
        config = SystemConfig(config_key=config_key, config_value=new_key)
        db.session.add(config)
        db.session.commit()

    is_valid = (auth_key == config.config_value)
    if not is_valid:
        return (False, 'invalid_key') if return_reason else False

    return (True, None) if return_reason else True

def generate_token(user_id):
    try:
        payload = {
            'exp': datetime.utcnow() + current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=24)),
            'iat': datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(
            payload,
            current_app.config.get('JWT_SECRET_KEY'),
            algorithm='HS256'
        )
    except Exception as e:
        return str(e)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token header format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY'), algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['sub']).first()
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

def token_required_page(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token')
        if not token:
            return redirect('/login')
        
        try:
            data = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY'), algorithms=["HS256"])
            current_user = User.query.get(data['sub'])
            if not current_user:
                return redirect('/login')
        except:
            return redirect('/login')
            
        return f(*args, **kwargs)
    
    return decorated

def log_audit(action, status, user_id=None, ip_address=None, details=None):
    from .. import db
    from ..models import AuditLog
    try:
        # Use request ip if not provided
        if not ip_address:
            # Check if we are in a request context
            try:
                ip_address = request.remote_addr
            except:
                ip_address = 'Internal'
            
        log = AuditLog(
            user_id=user_id,
            action=action,
            status=status,
            ip_address=ip_address,
            details=details
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
        db.session.rollback()
