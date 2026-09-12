"""
Header validation middleware for Polarion Mock Server.
Ensures mock behaves like production Polarion.

Measured against production (polarion-d.claas.local, 2026-09-11, HTTP 200):
the REST API v1 answers requests with ``Accept: application/json`` as well as
``Accept: */*``. Swagger UI sends ``accept: application/json``, the customer
fetch script sends ``Accept: application/json``, the client in this repo
sends ``Accept: */*``. All of them must work. Media types that Polarion cannot
produce (e.g. ``text/html``) are answered with 406 Not Acceptable.
"""

import logging
from flask import request, jsonify
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# Media ranges the REST API can satisfy (JSON:API is served as application/json)
ACCEPTABLE_MEDIA_RANGES = (
    "*/*",
    "application/*",
    "application/json",
    "application/vnd.api+json",
)


def _media_ranges(accept_header: str) -> List[str]:
    """Split an Accept header into bare media ranges (parameters stripped)."""
    ranges = []
    for item in accept_header.split(","):
        media = item.split(";", 1)[0].strip().lower()
        if media:
            ranges.append(media)
    return ranges


def accept_is_satisfiable(accept_header: str) -> bool:
    """True when the Accept header allows a JSON response."""
    if not accept_header:
        return True
    return any(media in ACCEPTABLE_MEDIA_RANGES for media in _media_ranges(accept_header))


def validate_headers_middleware() -> Optional[Tuple]:
    """
    Validate request headers according to Polarion requirements.

    - Accept must allow JSON (``*/*`` or ``application/json``), else 406
    - Content-Type of requests with a body must be application/json, else 415
    """
    # Skip validation for non-REST API endpoints
    if not request.path.startswith('/polarion/rest/v1'):
        return None

    # Skip for health check endpoints
    if request.path in ['/polarion/rest/v1/health']:
        return None

    # Check Accept header
    accept_header = request.headers.get('Accept', '')

    if not accept_is_satisfiable(accept_header):
        logger.warning(f"Not acceptable Accept header: {accept_header!r}")
        return jsonify({
            'errors': [{
                'status': '406',
                'title': 'Not Acceptable',
                'detail': f"Cannot produce a response matching Accept '{accept_header}'; "
                          f"use 'application/json' or '*/*'"
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
