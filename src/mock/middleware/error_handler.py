"""
Error handling middleware for Polarion Mock Server
Provides consistent error responses following JSON:API specification
"""

import logging
from typing import Dict, Any, List, Optional
from flask import jsonify, request

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API error class."""
    def __init__(self, message: str, status_code: int = 400, 
                 source: Optional[Dict[str, Any]] = None, 
                 meta: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.source = source
        self.meta = meta
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error for request data."""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        source = {'pointer': f'/data/attributes/{field}'} if field else None
        super().__init__(message, status_code=400, source=source, **kwargs)


class NotFoundError(APIError):
    """Resource not found error."""
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        # Special message for projects to match Polarion
        if resource_type == "projects":
            message = f"Project id {resource_id} does not exist."
        else:
            message = f"{resource_type} with id '{resource_id}' not found"
        source = {'resource': {'type': resource_type, 'id': resource_id}}
        super().__init__(message, status_code=404, source=source, **kwargs)


class ConflictError(APIError):
    """Resource conflict error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=409, **kwargs)


class ForbiddenError(APIError):
    """Access forbidden error."""
    def __init__(self, message: str = "Access forbidden", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class ServiceUnavailableError(APIError):
    """Service unavailable error."""
    def __init__(self, message: str = "Service temporarily unavailable", **kwargs):
        super().__init__(message, status_code=503, **kwargs)


def build_error_response(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build JSON:API compliant error response."""
    return {'errors': errors}


def error_to_dict(error: APIError) -> Dict[str, Any]:
    """Convert APIError to dictionary."""
    # Special handling for NotFoundError to match Polarion format
    if isinstance(error, NotFoundError) and error.status_code == 404:
        # Projects have a specific format
        if error.source and error.source.get('resource', {}).get('type') == 'projects':
            return {
                'status': '404',
                'title': 'Not Found',
                'detail': error.message
            }
        else:
            # General 404 format
            return {
                'status': '404',
                'title': 'Not Found',
                'detail': None,
                'source': None
            }
    
    error_dict = {
        'status': str(error.status_code),
        'title': error.__class__.__name__.replace('Error', ''),
        'detail': error.message
    }
    
    if error.source:
        error_dict['source'] = error.source
    
    if error.meta:
        error_dict['meta'] = error.meta
    
    return error_dict


def error_handler(error):
    """Handle API errors and return JSON:API compliant error responses."""
    if isinstance(error, APIError):
        # Handle custom API errors
        logger.warning(f"API Error: {error.message}", extra={
            'status_code': error.status_code,
            'error_type': error.__class__.__name__,
            'path': request.path,
            'method': request.method
        })
        
        response = jsonify(build_error_response([error_to_dict(error)]))
        response.status_code = error.status_code
        return response
    
    elif hasattr(error, 'code'):
        # Handle Flask HTTP errors
        status_code = error.code
        title = error.name if hasattr(error, 'name') else 'Error'
        detail = error.description if hasattr(error, 'description') else str(error)
        
        logger.error(f"HTTP Error: {detail}", extra={
            'status_code': status_code,
            'path': request.path,
            'method': request.method
        })
        
        error_dict = {
            'status': str(status_code),
            'title': title,
            'detail': detail
        }
        
        response = jsonify(build_error_response([error_dict]))
        response.status_code = status_code
        return response
    
    else:
        # Handle unexpected errors
        logger.exception("Unexpected error occurred", extra={
            'path': request.path,
            'method': request.method
        })
        
        error_dict = {
            'status': '500',
            'title': 'Internal Server Error',
            'detail': 'An unexpected error occurred'
        }
        
        response = jsonify(build_error_response([error_dict]))
        response.status_code = 500
        return response


def handle_validation_errors(errors: Dict[str, List[str]]) -> None:
    """Handle multiple validation errors."""
    error_list = []
    for field, messages in errors.items():
        for message in messages:
            error_list.append({
                'status': '400',
                'title': 'Validation Error',
                'detail': message,
                'source': {'pointer': f'/data/attributes/{field}'}
            })
    
    response = jsonify(build_error_response(error_list))
    response.status_code = 400
    return response