"""
Authentication middleware for Polarion Mock Server.

Production Polarion authenticates REST calls with a Personal Access Token
(PAT) sent as ``Authorization: Bearer <token>``. A PAT is an RS256 JWT signed
by the Polarion server; the mock cannot verify that signature, so it supports
three modes (``MOCK_AUTH_MODE``):

``pat`` (default)
    Behaves like Polarion for real PATs: any structurally valid JWT is
    accepted, the subject (``sub``) becomes the current user. Expiry is only
    enforced when ``MOCK_PAT_CHECK_EXPIRY=true`` (so an expired customer PAT
    still works offline). Mock JWTs signed with ``JWT_SECRET_KEY`` and tokens
    listed in ``MOCK_ACCEPTED_TOKENS`` / ``POLARION_PERSONAL_ACCESS_TOKEN`` are
    accepted as well.

``strict``
    Only mock JWTs signed with ``JWT_SECRET_KEY`` and explicitly listed tokens
    are accepted.

``disabled`` (or ``DISABLE_AUTH=true``)
    No authentication at all.

Every failure answers with a JSON:API error and HTTP 401, exactly like the
production server.
"""

import os
import jwt
import logging
from functools import wraps
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from flask import request, jsonify, current_app, g

logger = logging.getLogger(__name__)

AUTH_MODE_ENV = "MOCK_AUTH_MODE"
ACCEPTED_TOKENS_ENV = "MOCK_ACCEPTED_TOKENS"
PAT_ENV = "POLARION_PERSONAL_ACCESS_TOKEN"
PAT_CHECK_EXPIRY_ENV = "MOCK_PAT_CHECK_EXPIRY"

VALID_MODES = ("pat", "strict", "disabled")


class AuthError(Exception):
    """Authentication error exception."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def auth_mode() -> str:
    """Resolve the active authentication mode from the environment."""
    if _truthy(os.getenv("DISABLE_AUTH")):
        return "disabled"
    mode = (os.getenv(AUTH_MODE_ENV) or "pat").strip().lower()
    if mode not in VALID_MODES:
        logger.warning("Unknown %s=%r, falling back to 'pat'", AUTH_MODE_ENV, mode)
        mode = "pat"
    return mode


def accepted_tokens() -> List[str]:
    """Tokens that are always accepted (explicit allow-list)."""
    tokens: List[str] = []
    listed = os.getenv(ACCEPTED_TOKENS_ENV, "")
    tokens.extend(t.strip() for t in listed.split(",") if t.strip())
    pat = (os.getenv(PAT_ENV) or "").strip()
    if pat and not pat.startswith("your-"):
        tokens.append(pat)
    return tokens


def generate_mock_token(user_id: str = "admin", expires_in: int = 3600) -> str:
    """Generate a mock JWT token for testing."""
    secret_key = current_app.config.get('SECRET_KEY', 'dev-secret-key')
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'username': user_id,
        'sub': user_id,
        'exp': now + timedelta(seconds=expires_in),
        'iat': now,
        'permissions': ['read', 'write', 'admin']
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a token signed with the mock secret (HS256)."""
    secret_key = current_app.config.get('SECRET_KEY', 'dev-secret-key')
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired", 401)
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}", 401)


def _decode_unverified_pat(token: str) -> Dict[str, Any]:
    """Decode a Polarion-style PAT without checking its RS256 signature.

    Polarion PATs carry ``sub`` (user id), ``id``, ``iat`` and ``exp``. The
    signature cannot be checked outside Polarion, so only the structure (and
    optionally the expiry) is validated.
    """
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["RS256", "HS256", "ES256", "PS256"],
        )
    except jwt.DecodeError as error:
        raise AuthError(f"Invalid token: {error}", 401)
    except jwt.InvalidTokenError as error:
        raise AuthError(f"Invalid token: {error}", 401)

    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        expires = datetime.fromtimestamp(exp, tz=timezone.utc)
        if expires < datetime.now(timezone.utc):
            if _truthy(os.getenv(PAT_CHECK_EXPIRY_ENV)):
                raise AuthError("Token has expired", 401)
            logger.warning(
                "PAT for %s expired on %s - accepted because %s is not set",
                payload.get("sub"), expires.isoformat(), PAT_CHECK_EXPIRY_ENV,
            )
    return payload


def authenticate_bearer(token: str) -> Dict[str, Any]:
    """Resolve a bearer token to a user payload or raise AuthError.

    Order: mock JWT (signed with JWT_SECRET_KEY) -> explicit allow-list ->
    (pat mode only) unverified Polarion PAT.
    """
    if not token:
        raise AuthError("Empty bearer token", 401)

    mock_error: Optional[AuthError] = None
    try:
        payload = verify_token(token)
        payload.setdefault("auth", "mock-jwt")
        payload.setdefault("user_id", payload.get("sub", "mock-user"))
        payload.setdefault("username", payload["user_id"])
        return payload
    except AuthError as error:
        mock_error = error

    if token in accepted_tokens():
        return {
            "user_id": "pat-user",
            "username": "pat-user",
            "sub": "pat-user",
            "auth": "allow-list",
            "permissions": ["read", "write", "admin"],
        }

    if auth_mode() == "pat":
        payload = _decode_unverified_pat(token)
        user = payload.get("sub") or payload.get("user_id") or "pat-user"
        payload.setdefault("user_id", user)
        payload.setdefault("username", user)
        payload.setdefault("auth", "polarion-pat")
        payload.setdefault("permissions", ["read", "write", "admin"])
        return payload

    # strict mode: report the mock JWT error
    raise mock_error or AuthError("Invalid token", 401)


def _unauthorized(detail: str):
    return jsonify({
        'errors': [{
            'status': '401',
            'title': 'Unauthorized',
            'detail': detail
        }]
    }), 401


def auth_middleware():
    """Authentication middleware for all requests."""
    # Skip auth for health check and root endpoints
    if request.path in ['/', '/health']:
        return None

    if auth_mode() == "disabled":
        g.current_user = {'user_id': 'mock-user', 'username': 'mock-user', 'auth': 'disabled'}
        return None

    # Check for Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        # For /projects endpoint, return 401 to indicate API is available
        if request.path == '/polarion/rest/v1/projects' and request.method == 'GET':
            return _unauthorized('Authentication required. API is available.')
        return _unauthorized('Authorization header missing')

    # Extract token
    parts = auth_header.split(' ', 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return _unauthorized('Invalid authorization header format. Expected: Bearer <token>')

    token = parts[1].strip()

    try:
        payload = authenticate_bearer(token)
        g.current_user = payload
        logger.debug("Authenticated user: %s (%s)", payload.get('username'), payload.get('auth'))
    except AuthError as e:
        logger.warning("Authentication failed for %s %s: %s", request.method, request.path, e.message)
        return jsonify({
            'errors': [{
                'status': str(e.status_code),
                'title': 'Unauthorized',
                'detail': e.message
            }]
        }), e.status_code
    return None


def require_auth(f):
    """Decorator to require authentication for specific endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user'):
            return _unauthorized('Authentication required')
        return f(*args, **kwargs)
    return decorated_function


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return _unauthorized('Authentication required')

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
