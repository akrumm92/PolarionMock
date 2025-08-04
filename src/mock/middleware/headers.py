"""
Header validation middleware for Polarion Mock Server.
Ensures mock behaves exactly like production Polarion.
"""

import logging
from flask import request, jsonify
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_headers_middleware() -> Optional[Tuple]:
    """
    Validate request headers according to Polarion requirements.
    
    Critical requirement from POLARION_API_SPECIFICATION.md:
    - Accept header MUST be '*/*' for REST API v1
    - Other values return 406 Not Acceptable
    """
    # Skip validation for non-REST API endpoints
    if not request.path.startswith('/polarion/rest/v1'):
        return None
    
    # Skip for health check endpoints
    if request.path in ['/polarion/rest/v1/health']:
        return None
    
    # Check Accept header
    accept_header = request.headers.get('Accept', '')
    
    # Polarion REST API v1 requires Accept: */*
    if accept_header and accept_header != '*/*':
        logger.warning(f"Invalid Accept header: {accept_header}. Polarion requires '*/*'")
        return jsonify({
            'errors': [{
                'status': '406',
                'title': 'Not Acceptable',
                'detail': f"Accept header must be '*/*', got '{accept_header}'"
            }]
        }), 406
    
    # Check Content-Type for requests with body
    if request.method in ['POST', 'PUT', 'PATCH']:
        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('application/json') and request.data:
            return jsonify({
                'errors': [{
                    'status': '415',
                    'title': 'Unsupported Media Type',
                    'detail': 'Content-Type must be application/json'
                }]
            }), 415
    
    return None