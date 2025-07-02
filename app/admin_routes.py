from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from azure.cosmos import CosmosClient
import os
from datetime import datetime
import uuid
import functools

# Azure Configuration
ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
KEY = os.environ.get("COSMOSDB_KEY")
DATABASE_NAME = os.environ.get("COSMOSDB_DATABASE")
CONTAINER_NAME = os.environ.get("COSMOSDB_CONTAINER")

# Initialize CosmosClient
client = CosmosClient(ENDPOINT, credential=KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Blueprint for admin routes
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin role"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Admin page to manage users"""
    return render_template('admin/manage_users.html')

@admin_bp.route('/api/users')
@login_required
@admin_required
def get_users():
    """API endpoint to get all users for admin"""
    query = "SELECT c.id, c.username, c.email, c.role, c.status, c._ts FROM c WHERE c.type = 'user' ORDER BY c._ts DESC"
    users = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    return jsonify({'users': users})

@admin_bp.route('/api/users/<user_id>/status', methods=['PUT'])
@login_required
@admin_required
def update_user_status(user_id):
    """API endpoint to update user status"""
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['unverified', 'active', 'inactive']:
        return jsonify({'error': 'Invalid status'}), 400
    
    # Get the user
    query = f"SELECT * FROM c WHERE c.type = 'user' AND c.id = '{user_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        return jsonify({'error': 'User not found'}), 404
    
    user = items[0]
    
    # Don't allow changing admin user status
    if user.get('role') == 'admin':
        return jsonify({'error': 'Cannot change admin user status'}), 403
    
    # Update user status
    user['status'] = new_status
    container.replace_item(item=user['id'], body=user)
    
    # Log this activity
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'type': 'activity',
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': 'user_status_update',
            'message': f"Updated user '{user['username']}' status to '{new_status}'",
            'target_user': user['username']
        }
        container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
    
    return jsonify({'success': True, 'message': f"User status updated to {new_status}"})

@admin_bp.route('/api/pending_users')
@login_required
@admin_required
def get_pending_users():
    """API endpoint to get users pending verification"""
    print(f"get_pending_users called by user: {current_user.username}, role: {current_user.role}")
    
    query = "SELECT c.id, c.username, c.email, c._ts FROM c WHERE c.type = 'user' AND c.status = 'unverified' ORDER BY c._ts DESC"
    users = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    print(f"Found {len(users)} pending users")
    
    return jsonify({'users': users, 'count': len(users)})

@admin_bp.route('/api/users/<user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    """API endpoint to approve a user (set status to active)"""
    # Get the user
    query = f"SELECT * FROM c WHERE c.type = 'user' AND c.id = '{user_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        return jsonify({'error': 'User not found'}), 404
    
    user = items[0]
    
    # Update user status to active
    user['status'] = 'active'
    container.replace_item(item=user['id'], body=user)
    
    # Log this activity
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'type': 'activity',
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': 'user_approved',
            'message': f"Approved user '{user['username']}'",
            'target_user': user['username']
        }
        container.create_item(body=activity)
    except Exception:
        pass
    
    return jsonify({'success': True, 'message': f"User {user['username']} has been approved"})
