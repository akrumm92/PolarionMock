"""
Logging middleware and configuration for Polarion Mock Server
"""

import os
import logging
import json
from datetime import datetime
from typing import Optional

from flask import request, g
import structlog
from pythonjsonlogger import jsonlogger


def setup_logging(name: str) -> logging.Logger:
    """Set up structured logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('LOG_FORMAT', 'json').lower()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create handler
    handler = logging.StreamHandler()
    
    if log_format == 'json':
        # JSON format for production
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            timestamp=True
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Also setup structlog for structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if log_format == 'json' else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return logger


def request_logging_middleware():
    """Log incoming requests and outgoing responses."""
    if not os.getenv('ENABLE_REQUEST_LOGGING', 'True').lower() == 'true':
        return None
    
    # Generate request ID
    g.request_id = f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    g.request_start_time = datetime.utcnow()
    
    logger = logging.getLogger(__name__)
    
    # Log request
    logger.info("Request received", extra={
        'request_id': g.request_id,
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'content_length': request.content_length,
        'query_params': dict(request.args) if request.args else None
    })
    
    # Log request body for debugging (be careful with sensitive data)
    if request.method in ['POST', 'PATCH', 'PUT'] and request.content_length and request.content_length < 10000:
        try:
            if request.is_json:
                logger.debug("Request body", extra={
                    'request_id': g.request_id,
                    'body': request.get_json()
                })
        except Exception:
            pass


def log_response(response):
    """Log response details."""
    if not os.getenv('ENABLE_REQUEST_LOGGING', 'True').lower() == 'true':
        return response
    
    logger = logging.getLogger(__name__)
    
    # Calculate request duration
    duration_ms = None
    if hasattr(g, 'request_start_time'):
        duration = datetime.utcnow() - g.request_start_time
        duration_ms = duration.total_seconds() * 1000
    
    # Log response
    logger.info("Request completed", extra={
        'request_id': getattr(g, 'request_id', 'unknown'),
        'status_code': response.status_code,
        'content_length': response.content_length,
        'duration_ms': duration_ms
    })
    
    return response


class RequestContextLogger:
    """Logger that automatically includes request context."""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
    
    def _log(self, level: str, message: str, **kwargs):
        """Log with request context."""
        extra = kwargs.get('extra', {})
        extra['request_id'] = getattr(g, 'request_id', 'no-request')
        if hasattr(g, 'current_user'):
            extra['user_id'] = g.current_user.get('user_id')
        kwargs['extra'] = extra
        getattr(self.logger, level)(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log('critical', message, **kwargs)