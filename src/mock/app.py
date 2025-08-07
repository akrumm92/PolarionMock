"""
Polarion Mock Server - Flask Application
Provides a complete mock implementation of the Polarion REST API
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from dotenv import load_dotenv

from .middleware.auth import auth_middleware
from .middleware.logging import setup_logging, request_logging_middleware
from .middleware.error_handler import error_handler, ValidationError, NotFoundError
from .middleware.headers import validate_headers_middleware
from .middleware.response_padding import pad_response_middleware
from .api import projects, workitems, documents, collections, enumerations, document_parts
from .utils.response_builder import JSONAPIResponseBuilder

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging(__name__)


def create_app(config: Dict[str, Any] = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Apply configuration
    if config:
        app.config.update(config)
    else:
        # Default configuration
        app.config.update(
            DEBUG=os.getenv('MOCK_DEBUG', 'True').lower() == 'true',
            HOST=os.getenv('MOCK_HOST', '0.0.0.0'),
            PORT=int(os.getenv('MOCK_PORT', 5001)),  # Default 5001 to avoid macOS AirPlay
            SECRET_KEY=os.getenv('JWT_SECRET_KEY', 'dev-secret-key'),
            JSON_SORT_KEYS=False,
            JSONIFY_PRETTYPRINT_REGULAR=True
        )
    
    # Enable CORS
    CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))
    
    # Register middleware
    app.before_request(request_logging_middleware)
    app.before_request(validate_headers_middleware)
    app.before_request(auth_middleware)
    app.after_request(pad_response_middleware)
    
    # Register error handlers
    app.register_error_handler(ValidationError, error_handler)
    app.register_error_handler(NotFoundError, error_handler)
    app.register_error_handler(404, error_handler)
    app.register_error_handler(500, error_handler)
    
    # Register blueprints
    app.register_blueprint(projects.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(workitems.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(documents.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(document_parts.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(collections.bp, url_prefix='/polarion/rest/v1')
    app.register_blueprint(enumerations.bp, url_prefix='/polarion/rest/v1')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0',
            'api_version': 'v1'
        })
    
    # Root endpoint
    @app.route('/')
    def root():
        """Root endpoint with API information."""
        return jsonify({
            'name': 'Polarion Mock Server',
            'version': '1.0.0',
            'api_base': '/polarion/rest/v1',
            'documentation': '/polarion/rest/v1/docs',
            'health': '/health'
        })
    
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
    
    logger.info("Polarion Mock Server initialized")
    return app


def run_server():
    """Run the Flask development server."""
    app = create_app()
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5001)  # Default 5001 to avoid macOS AirPlay
    debug = app.config.get('DEBUG', True)
    
    logger.info(f"Starting Polarion Mock Server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()