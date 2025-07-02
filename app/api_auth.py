from functools import wraps
from flask import request, jsonify
from .auth import get_user_by_api_key

def api_key_required(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None
        
        # Check for API key in headers
        if 'X-API-Key' in request.headers:
            api_key = request.headers['X-API-Key']
        # Check for API key in query parameters
        elif 'api_key' in request.args:
            api_key = request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401
        
        # Validate API key
        user = get_user_by_api_key(api_key)
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Check if user is active
        if user.status != 'active' and user.role != 'admin':
            return jsonify({'error': 'User account is not active'}), 403
        
        # Add user to request context
        request.api_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_api_user():
    """Get the current authenticated API user"""
    return getattr(request, 'api_user', None)
