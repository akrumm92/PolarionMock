"""
Custom exceptions for Polarion API client.
"""

from typing import Optional, Dict, Any, List


class PolarionError(Exception):
    """Base exception for all Polarion API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None):
        """Initialize Polarion error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Raw response data from API
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        self.errors = self._extract_errors(response_data)
    
    def _extract_errors(self, response_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract error details from API response."""
        if not response_data:
            return []
        
        if "errors" in response_data and isinstance(response_data["errors"], list):
            return response_data["errors"]
        
        return []
    
    def __str__(self) -> str:
        """String representation of error."""
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class PolarionAuthError(PolarionError):
    """Authentication error (401)."""
    
    def __init__(self, message: str = "Authentication failed", 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, response_data=response_data)


class PolarionNotFoundError(PolarionError):
    """Resource not found error (404)."""
    
    def __init__(self, resource_type: str, resource_id: str, 
                 response_data: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(message, status_code=404, response_data=response_data)
        self.resource_type = resource_type
        self.resource_id = resource_id


class PolarionValidationError(PolarionError):
    """Validation error (400)."""
    
    def __init__(self, message: str = "Validation failed", 
                 validation_errors: Optional[List[str]] = None,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, response_data=response_data)
        self.validation_errors = validation_errors or []


class PolarionServerError(PolarionError):
    """Server error (5xx)."""
    
    def __init__(self, message: str = "Server error", status_code: int = 500,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status_code, response_data=response_data)


class PolarionTimeoutError(PolarionError):
    """Request timeout error."""
    
    def __init__(self, message: str = "Request timed out", timeout: Optional[int] = None):
        super().__init__(message)
        self.timeout = timeout


class PolarionConnectionError(PolarionError):
    """Connection error."""
    
    def __init__(self, message: str = "Failed to connect to Polarion", 
                 url: Optional[str] = None):
        super().__init__(message)
        self.url = url