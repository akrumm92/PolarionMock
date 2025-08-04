"""
Tests for the exceptions module.
"""

import pytest
from polarion_api.exceptions import (
    PolarionError,
    PolarionAuthError,
    PolarionNotFoundError,
    PolarionValidationError,
    PolarionServerError,
    PolarionTimeoutError,
    PolarionConnectionError
)


class TestExceptions:
    """Test custom exception classes."""
    
    @pytest.mark.unit
    def test_polarion_error_basic(self):
        """Test basic PolarionError."""
        error = PolarionError("Test error")
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.response_data is None
        assert error.errors == []
    
    @pytest.mark.unit
    def test_polarion_error_with_status(self):
        """Test PolarionError with status code."""
        error = PolarionError("Test error", status_code=400)
        
        assert str(error) == "[400] Test error"
        assert error.status_code == 400
    
    @pytest.mark.unit
    def test_polarion_error_with_response_data(self):
        """Test PolarionError with response data."""
        response_data = {
            "errors": [
                {"status": "400", "title": "Bad Request", "detail": "Invalid field"},
                {"status": "400", "title": "Bad Request", "detail": "Missing required field"}
            ]
        }
        error = PolarionError("Test error", status_code=400, response_data=response_data)
        
        assert error.errors == response_data["errors"]
        assert len(error.errors) == 2
    
    @pytest.mark.unit
    def test_polarion_auth_error(self):
        """Test PolarionAuthError."""
        error = PolarionAuthError()
        
        assert error.message == "Authentication failed"
        assert error.status_code == 401
        assert str(error) == "[401] Authentication failed"
    
    @pytest.mark.unit
    def test_polarion_auth_error_custom_message(self):
        """Test PolarionAuthError with custom message."""
        error = PolarionAuthError("Invalid token")
        
        assert error.message == "Invalid token"
        assert error.status_code == 401
    
    @pytest.mark.unit
    def test_polarion_not_found_error(self):
        """Test PolarionNotFoundError."""
        error = PolarionNotFoundError("workitem", "myproject/REQ-123")
        
        assert error.message == "workitem with ID 'myproject/REQ-123' not found"
        assert error.status_code == 404
        assert error.resource_type == "workitem"
        assert error.resource_id == "myproject/REQ-123"
        assert str(error) == "[404] workitem with ID 'myproject/REQ-123' not found"
    
    @pytest.mark.unit
    def test_polarion_validation_error(self):
        """Test PolarionValidationError."""
        error = PolarionValidationError()
        
        assert error.message == "Validation failed"
        assert error.status_code == 400
        assert error.validation_errors == []
    
    @pytest.mark.unit
    def test_polarion_validation_error_with_errors(self):
        """Test PolarionValidationError with validation errors."""
        validation_errors = [
            "Title is required",
            "Invalid work item type"
        ]
        error = PolarionValidationError(
            message="Custom validation failed",
            validation_errors=validation_errors
        )
        
        assert error.message == "Custom validation failed"
        assert error.validation_errors == validation_errors
        assert len(error.validation_errors) == 2
    
    @pytest.mark.unit
    def test_polarion_server_error(self):
        """Test PolarionServerError."""
        error = PolarionServerError()
        
        assert error.message == "Server error"
        assert error.status_code == 500
        assert str(error) == "[500] Server error"
    
    @pytest.mark.unit
    def test_polarion_server_error_custom(self):
        """Test PolarionServerError with custom values."""
        error = PolarionServerError("Internal server error", status_code=503)
        
        assert error.message == "Internal server error"
        assert error.status_code == 503
        assert str(error) == "[503] Internal server error"
    
    @pytest.mark.unit
    def test_polarion_timeout_error(self):
        """Test PolarionTimeoutError."""
        error = PolarionTimeoutError()
        
        assert error.message == "Request timed out"
        assert error.timeout is None
    
    @pytest.mark.unit
    def test_polarion_timeout_error_with_timeout(self):
        """Test PolarionTimeoutError with timeout value."""
        error = PolarionTimeoutError("Request timed out after 30s", timeout=30)
        
        assert error.message == "Request timed out after 30s"
        assert error.timeout == 30
    
    @pytest.mark.unit
    def test_polarion_connection_error(self):
        """Test PolarionConnectionError."""
        error = PolarionConnectionError()
        
        assert error.message == "Failed to connect to Polarion"
        assert error.url is None
    
    @pytest.mark.unit
    def test_polarion_connection_error_with_url(self):
        """Test PolarionConnectionError with URL."""
        error = PolarionConnectionError(
            "Connection refused",
            url="https://polarion.example.com"
        )
        
        assert error.message == "Connection refused"
        assert error.url == "https://polarion.example.com"
    
    @pytest.mark.unit
    def test_exception_inheritance(self):
        """Test that all exceptions inherit from PolarionError."""
        # Create instances
        errors = [
            PolarionAuthError(),
            PolarionNotFoundError("test", "123"),
            PolarionValidationError(),
            PolarionServerError(),
            PolarionTimeoutError(),
            PolarionConnectionError()
        ]
        
        # All should be instances of PolarionError
        for error in errors:
            assert isinstance(error, PolarionError)
            assert isinstance(error, Exception)
    
    @pytest.mark.unit
    def test_exception_response_data_extraction(self):
        """Test error extraction from various response formats."""
        # Test with errors list
        response1 = {
            "errors": [
                {"status": "400", "detail": "Error 1"},
                {"status": "400", "detail": "Error 2"}
            ]
        }
        error1 = PolarionError("Test", response_data=response1)
        assert len(error1.errors) == 2
        
        # Test with empty errors
        response2 = {"errors": []}
        error2 = PolarionError("Test", response_data=response2)
        assert error2.errors == []
        
        # Test with no errors key
        response3 = {"message": "Some error"}
        error3 = PolarionError("Test", response_data=response3)
        assert error3.errors == []
        
        # Test with non-list errors
        response4 = {"errors": "Invalid format"}
        error4 = PolarionError("Test", response_data=response4)
        assert error4.errors == []