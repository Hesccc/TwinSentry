from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from ..models import User, db
from ..services.utils import generate_token, token_required, log_audit
import os
from werkzeug.utils import secure_filename

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and user.check_password(data.get('password')):
        token = generate_token(user.id)
        log_audit('用户登录', '成功', user_id=user.id, details=f"用户: {user.username}")
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'avatar': user.avatar
            }
        }), 200
    
    log_audit('用户登录', '失败', ip_address=request.remote_addr, details=f"尝试用户名: {data.get('username')}")
    return jsonify({'message': 'Invalid credentials'}), 401

@auth.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    log_audit('用户注销', '成功', user_id=current_user.id, ip_address=request.remote_addr, details=f"用户: {current_user.username}")
    return jsonify({'message': 'Logged out successfully'})

@auth.route('/profile', methods=['GET', 'PUT'])
@token_required
def profile(current_user):
    if request.method == 'GET':
        return jsonify({
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'avatar': current_user.avatar
        })
    
    data = request.get_json()
    if 'username' in data:
        current_user.username = data['username']
    if 'email' in data:
        current_user.email = data['email']
    if 'password' in data and data['password']:
        current_user.set_password(data['password'])
        
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'})

@auth.route('/avatar', methods=['POST'])
@token_required
def upload_avatar(current_user):
    if 'avatar' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(f"user_{current_user.id}_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Update user record
        current_user.avatar = f"/static/uploads/avatars/{filename}"
        db.session.commit()
        
        return jsonify({'avatar_url': current_user.avatar})
    
    return jsonify({'message': 'Upload failed'}), 400
