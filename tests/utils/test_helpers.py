"""
Test helper functions with enhanced logging
"""

import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import requests


class APITestClient:
    """Enhanced API client with automatic logging."""
    
    def __init__(self, base_url: str, auth_headers: Dict[str, str], logger: logging.Logger, capture_api_calls=None):
        self.base_url = base_url
        self.auth_headers = auth_headers
        self.logger = logger
        self.capture_api_calls = capture_api_calls
        
    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details."""
        self.logger.info(f"API Request: {method} {url}")
        if 'json' in kwargs:
            self.logger.debug(f"Request Body: {json.dumps(kwargs['json'], indent=2)}")
        if 'params' in kwargs:
            self.logger.debug(f"Query Params: {kwargs['params']}")
            
    def _log_response(self, response: requests.Response, duration: float):
        """Log response details."""
        self.logger.info(f"API Response: {response.status_code} ({duration:.2f}s)")
        
        try:
            if response.content:
                response_data = response.json()
                self.logger.debug(f"Response Body: {json.dumps(response_data, indent=2)}")
        except:
            self.logger.debug(f"Response Body (text): {response.text[:500]}")
            
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request with automatic logging."""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth headers
        headers = kwargs.get('headers', {})
        headers.update(self.auth_headers)
        kwargs['headers'] = headers
        
        # Log request
        self._log_request(method, url, **kwargs)
        
        # Make request and measure time
        start_time = time.time()
        response = requests.request(method, url, **kwargs)
        duration = time.time() - start_time
        
        # Log response
        self._log_response(response, duration)
        
        # Capture for analysis if provided
        if self.capture_api_calls:
            request_data = kwargs.get('json')
            try:
                response_data = response.json() if response.content else None
            except:
                response_data = None
                
            self.capture_api_calls(
                method=method,
                url=url,
                status_code=response.status_code,
                response_time=duration,
                request_data=request_data,
                response_data=response_data
            )
        
        return response
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET request."""
        return self.request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST request."""
        return self.request('POST', endpoint, **kwargs)
    
    def patch(self, endpoint: str, **kwargs) -> requests.Response:
        """PATCH request."""
        return self.request('PATCH', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE request."""
        return self.request('DELETE', endpoint, **kwargs)


def log_test_data(logger: logging.Logger, data_type: str, data: Any):
    """Log test data in a structured format."""
    logger.info(f"Test Data - {data_type}:")
    if isinstance(data, (dict, list)):
        logger.info(json.dumps(data, indent=2))
    else:
        logger.info(str(data))


def assert_with_logging(logger: logging.Logger, condition: bool, message: str, actual: Any = None, expected: Any = None):
    """Assert with detailed logging."""
    if condition:
        logger.debug(f"✓ Assertion passed: {message}")
    else:
        logger.error(f"✗ Assertion failed: {message}")
        if actual is not None:
            logger.error(f"  Actual: {actual}")
        if expected is not None:
            logger.error(f"  Expected: {expected}")
    assert condition, message


def log_test_section(logger: logging.Logger, section_name: str):
    """Log a test section separator."""
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(f"{section_name}")
    logger.info(f"{separator}\n")