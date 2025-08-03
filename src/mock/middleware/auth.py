"""
Authentication middleware for Polarion Mock Server
Simulates Polarion's JWT-based authentication
"""

import os
import jwt
import logging
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from flask import request, jsonify, current_app, g

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Authentication error exception."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def generate_mock_token(user_id: str = "admin", expires_in: int = 3600) -> str:
    """Generate a mock JWT token for testing."""
    secret_key = current_app.config.get('SECRET_KEY', 'dev-secret-key')
    
    payload = {
        'user_id': user_id,
        'username': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow(),
        'permissions': ['read', 'write', 'admin']
    }
    
    return jwt.encode(payload, secret_key, algorithm='HS256')


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token."""
    secret_key = current_app.config.get('SECRET_KEY', 'dev-secret-key')
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired", 401)
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}", 401)


def auth_middleware():
    """Authentication middleware for all requests."""
    # Skip auth for health check and root endpoints
    if request.path in ['/', '/health']:
        return None
    
    # Skip auth if disabled
    if os.getenv('DISABLE_AUTH', 'false').lower() == 'true':
        g.current_user = {'user_id': 'mock-user', 'username': 'mock-user'}
        return None
    
    # Check for Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        # For /projects endpoint, return 401 to indicate API is available
        if request.path == '/polarion/rest/v1/projects' and request.method == 'GET':
            return jsonify({
                'errors': [{
                    'status': '401',
                    'title': 'Unauthorized',
                    'detail': 'Authentication required. API is available.'
                }]
            }), 401
        
        return jsonify({
            'errors': [{
                'status': '401',
                'title': 'Unauthorized',
                'detail': 'Authorization header missing'
            }]
        }), 401
    
    # Extract token
    parts = auth_header.split(' ')
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return jsonify({
            'errors': [{
                'status': '401',
                'title': 'Unauthorized',
                'detail': 'Invalid authorization header format. Expected: Bearer <token>'
            }]
        }), 401
    
    token = parts[1]
    
    try:
        # Verify token
        payload = verify_token(token)
        g.current_user = payload
        logger.debug(f"Authenticated user: {payload.get('username')}")
    except AuthError as e:
        return jsonify({
            'errors': [{
                'status': str(e.status_code),
                'title': 'Unauthorized',
                'detail': e.message
            }]
        }), e.status_code


def require_auth(f):
    """Decorator to require authentication for specific endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user'):
            return jsonify({
                'errors': [{
                    'status': '401',
                    'title': 'Unauthorized',
                    'detail': 'Authentication required'
                }]
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return jsonify({
                    'errors': [{
                        'status': '401',
                        'title': 'Unauthorized',
                        'detail': 'Authentication required'
                    }]
                }), 401
            
            user_permissions = g.current_user.get('permissions', [])
            if permission not in user_permissions:
                return jsonify({
                    'errors': [{
                        'status': '403',
                        'title': 'Forbidden',
                        'detail': f'Permission "{permission}" required'
                    }]
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator