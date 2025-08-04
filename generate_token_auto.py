#!/usr/bin/env python3
"""
Generate JWT token for Polarion Mock API authentication - Non-interactive version
"""

import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET_KEY not found in environment variables. Please check your .env file.")

# Token parameters
import sys
user_id = sys.argv[1] if len(sys.argv) > 1 else "admin"
username = user_id  # Use same as user_id
expiry_hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24

# Create token payload
now = datetime.utcnow()
expiry = now + timedelta(hours=expiry_hours)

payload = {
    "user_id": user_id,
    "username": username,
    "exp": int(expiry.timestamp()),
    "iat": int(now.timestamp()),
    "permissions": ["read", "write", "admin"]
}

# Generate token
token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

print(f"\nGenerated JWT token for user '{username}' (expires in {expiry_hours} hours):")
print(f"\nToken: {token}")
print(f"\nUsage examples:")
print(f'curl -H "Authorization: Bearer {token}" http://localhost:5001/polarion/rest/v1/projects')
print(f'\nexport AUTH_TOKEN="Bearer {token}"')
print(f'curl -H "Authorization: $AUTH_TOKEN" http://localhost:5001/polarion/rest/v1/projects')