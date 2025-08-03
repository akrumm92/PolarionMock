#!/usr/bin/env python3
"""
Generate a JWT token for testing the Polarion Mock API
"""

import os
import sys
from datetime import datetime, timedelta
import jwt

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def generate_token(user_id="admin", expires_in_hours=24):
    """Generate a JWT token for testing."""
    # Get secret key from environment or use default
    secret_key = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    
    payload = {
        'user_id': user_id,
        'username': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow(),
        'permissions': ['read', 'write', 'admin']
    }
    
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token

if __name__ == "__main__":
    print("=== Polarion Mock JWT Token Generator ===\n")
    
    # Check if auth is disabled
    if os.getenv('DISABLE_AUTH', 'false').lower() == 'true':
        print("⚠️  WARNING: Authentication is currently DISABLED in .env file")
        print("   Set DISABLE_AUTH=false to enable authentication\n")
    
    # Generate token
    user_id = input("Enter user ID (default: admin): ").strip() or "admin"
    hours = input("Token validity in hours (default: 24): ").strip() or "24"
    
    try:
        hours = int(hours)
    except ValueError:
        hours = 24
    
    token = generate_token(user_id, hours)
    
    print(f"\n✅ Token generated for user '{user_id}' (valid for {hours} hours):\n")
    print(f"Bearer {token}\n")
    
    print("Usage examples:")
    print(f"curl -H \"Authorization: Bearer {token}\" http://localhost:5001/polarion/rest/v1/projects")
    print(f"\nexport AUTH_TOKEN=\"Bearer {token}\"")
    print("curl -H \"Authorization: $AUTH_TOKEN\" http://localhost:5001/polarion/rest/v1/projects")