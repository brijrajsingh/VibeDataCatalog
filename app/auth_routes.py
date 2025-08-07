from flask import render_template, current_app as app, request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required, logout_user, login_user
from .cosmos_client import users_container, activities_container
import uuid
from datetime import datetime

@app.route('/profile')
def profile():
    """User profile page."""
    if not current_user.is_authenticated:
        return render_template('login.html')
    return render_template('auth/profile.html', name=current_user.username)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Allow user to change their own password"""
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'success': False, 'error': 'Both current and new passwords are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'error': 'New password must be at least 6 characters long'}), 400
    
    # Get the current user from users container
    query = f"SELECT * FROM c WHERE c.id = '{current_user.id}'"
    items = list(users_container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    user = items[0]
    
    # Verify current password
    from werkzeug.security import check_password_hash, generate_password_hash
    if not check_password_hash(user['password'], current_password):
        return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
    
    # Hash the new password
    hashed_password = generate_password_hash(new_password)
    
    # Update user password
    user['password'] = hashed_password
    users_container.replace_item(item=user['id'], body=user)
    
    # Log this activity in activities container
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': 'password_changed_self',
            'message': f"User '{current_user.username}' changed their own password"
        }
        activities_container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
    
    return jsonify({'success': True, 'message': 'Password changed successfully'})
