"""
Polarion Mock Server - Flask Application
Provides a complete mock implementation of the Polarion REST API

Environment (see .env.example):
    MOCK_HOST / MOCK_PORT      bind address (default 0.0.0.0:5001)
    MOCK_DEBUG                 Flask debug mode (default false)
    MOCK_SSL                   true -> serve HTTPS with a self-signed
                               certificate (like a production Polarion behind
                               a self-signed cert; use verify-ssl=false)
    MOCK_SSL_CERT/MOCK_SSL_KEY optional PEM files instead of the ad-hoc cert
    MOCK_AUTH_MODE             pat (default) | strict | disabled
    MOCK_DUMP_DIR              extra directories with Polarion document dumps
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union, Tuple

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from dotenv import load_dotenv

from .middleware.auth import auth_middleware, auth_mode
from .middleware.logging import setup_logging, request_logging_middleware
from .middleware.error_handler import error_handler, ValidationError, NotFoundError, APIError
from .middleware.headers import validate_headers_middleware
from .middleware.response_padding import pad_response_middleware
from .api import projects, workitems, documents, collections, enumerations, document_parts, mock_admin, comments
from .utils.response_builder import JSONAPIResponseBuilder

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging(__name__)

MOCK_VERSION = "1.1.0"


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def create_app(config: Dict[str, Any] = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Apply configuration
    if config:
        app.config.update(config)
    else:
        # Default configuration
        app.config.update(
            DEBUG=_truthy(os.getenv('MOCK_DEBUG', 'false')),
            HOST=os.getenv('MOCK_HOST', '0.0.0.0'),
            PORT=int(os.getenv('MOCK_PORT', 5001)),  # Default 5001 to avoid macOS AirPlay
            SECRET_KEY=os.getenv('JWT_SECRET_KEY', 'dev-secret-key'),
            JSON_SORT_KEYS=False,
            JSONIFY_PRETTYPRINT_REGULAR=True
        )
    app.config.setdefault('SECRET_KEY', os.getenv('JWT_SECRET_KEY', 'dev-secret-key'))
    # Polarion returns UTF-8 JSON as-is (umlauts are not \u-escaped)
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    # Enable CORS
    CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))

    # Register middleware
    app.before_request(request_logging_middleware)
    app.before_request(validate_headers_middleware)
    app.before_request(auth_middleware)
    app.after_request(pad_response_middleware)

    # Register error handlers
    app.register_error_handler(APIError, error_handler)
    app.register_error_handler(ValidationError, error_handler)
    app.register_error_handler(NotFoundError, error_handler)
    app.register_error_handler(404, error_handler)
    app.register_error_handler(405, error_handler)
    app.register_error_handler(500, error_handler)

    # Register blueprints
    # NOTE: document_parts owns GET/POST .../documents/{name}/parts
    app.register_blueprint(document_parts.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(projects.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(workitems.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(comments.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(documents.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(collections.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(enumerations.bp, url_prefix='/polarion/rest/v1')
    # Mock-only administration (outside the Polarion namespace)
    app.register_blueprint(mock_admin.bp)

    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        from .storage.data_store import data_store
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'version': MOCK_VERSION,
            'api_version': 'v1',
            'auth_mode': auth_mode(),
            'documents': len(data_store.documents),
            'workitems': len(data_store.workitems),
            'dumps': [s['document_id'] for s in data_store.dump_summaries],
        })

    # Root endpoint
    @app.route('/')
    def root():
        """Root endpoint with API information."""
        return jsonify({
            'name': 'Polarion Mock Server',
            'version': MOCK_VERSION,
            'api_base': '/polarion/rest/v1',
            'documentation': '/polarion/rest/v1/docs',
            'health': '/health',
            'admin': '/mock/admin/documents'
        })

    # Legacy API root: production returns HTML here (used for auth probes)
    @app.route('/polarion/api')
    def legacy_api_root():
        return Response("<html><body><h1>Polarion</h1></body></html>", mimetype='text/html')

    # API root endpoint
    @app.route('/polarion/rest/v1')
    def api_root():
        """API root endpoint following JSON:API specification."""
        response_builder = JSONAPIResponseBuilder()
        return response_builder.build_response(
            data={
                'type': 'api-info',
                'id': 'v1',
                'attributes': {
                    'version': 'v1',
                    'name': 'Polarion REST API Mock',
                    'description': 'Mock implementation of Polarion ALM REST API',
                    'json_api_version': '1.0'
                },
                'links': {
                    'self': '/polarion/rest/v1',
                    'projects': '/polarion/rest/v1/projects',
                    'workitems': '/polarion/rest/v1/all/workitems',
                    'documents': '/polarion/rest/v1/all/documents',
                    'enumerations': '/polarion/rest/v1/enumerations'
                }
            }
        )

    logger.info("Polarion Mock Server initialized (auth mode: %s)", auth_mode())
    return app


def ssl_context_from_env() -> Optional[Union[str, Tuple[str, str]]]:
    """SSL context for app.run(): None (HTTP), 'adhoc' or (cert, key)."""
    cert = os.getenv('MOCK_SSL_CERT')
    key = os.getenv('MOCK_SSL_KEY')
    if cert and key:
        return (cert, key)
    if _truthy(os.getenv('MOCK_SSL')):
        return 'adhoc'
    return None


def _bind_hosts(host: str) -> list:
    """Hosts to bind. ``0.0.0.0``/``::``/empty -> IPv4 AND IPv6 (dual stack).

    ``localhost`` resolves to ``::1`` first on Windows; a server that listens
    on IPv4 only costs ~2 s per request while the client falls back to
    ``127.0.0.1``. Binding both families makes ``https://localhost:5001``
    as fast as ``https://127.0.0.1:5001``.
    """
    if host in ('', '0.0.0.0', '::', '*'):
        return ['0.0.0.0', '::']
    return [host]


def run_server():
    """Run the development server (dual stack, optional HTTPS, no reloader)."""
    import threading
    from werkzeug.serving import make_server, generate_adhoc_ssl_context, load_ssl_context

    app = create_app()
    host = app.config.get('HOST', '0.0.0.0')
    port = int(app.config.get('PORT', 5001))  # Default 5001 to avoid macOS AirPlay
    ssl_context = ssl_context_from_env()
    if ssl_context == 'adhoc':
        ssl_context = generate_adhoc_ssl_context()
    elif isinstance(ssl_context, tuple):
        ssl_context = load_ssl_context(*ssl_context)
    scheme = 'https' if ssl_context else 'http'

    from .storage.data_store import data_store
    logger.info("Starting Polarion Mock Server on %s://%s:%s (auth mode: %s)", scheme, host, port, auth_mode())
    for summary in data_store.dump_summaries:
        logger.info("Serving dumped document %s (%d parts, %d work items)",
                    summary['document_id'], summary['parts'], summary['workitems'])

    servers = []
    for bind_host in _bind_hosts(host):
        try:
            servers.append(make_server(bind_host, port, app, threaded=True, ssl_context=ssl_context))
            logger.info("Listening on %s://%s:%s", scheme, bind_host, port)
        except OSError as error:
            # e.g. no IPv6 on this machine - IPv4 alone is fine
            logger.warning("Cannot bind %s:%s (%s)", bind_host, port, error)
    if not servers:
        raise SystemExit(f"Polarion mock: cannot bind port {port}")

    # The reloader would import (and seed) the data store twice - not used.
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in servers[1:]]
    for thread in threads:
        thread.start()
    try:
        servers[0].serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            server.shutdown()


if __name__ == '__main__':
    run_server()
