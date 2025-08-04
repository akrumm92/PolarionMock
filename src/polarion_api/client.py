"""
Main Polarion API client.
"""

import logging
import warnings
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from .config import PolarionConfig
from .exceptions import (
    PolarionError,
    PolarionAuthError,
    PolarionNotFoundError,
    PolarionValidationError,
    PolarionServerError,
    PolarionTimeoutError,
    PolarionConnectionError
)
from .work_items import WorkItemsMixin
from .documents import DocumentsMixin
from .utils import build_query_params

logger = logging.getLogger(__name__)


class PolarionClient(WorkItemsMixin, DocumentsMixin):
    """Main client for interacting with Polarion API.
    
    Example:
        >>> from polarion_api import PolarionClient
        >>> client = PolarionClient()
        >>> projects = client.get_projects()
    """
    
    def __init__(self, config: Optional[PolarionConfig] = None):
        """Initialize Polarion client.
        
        Args:
            config: Configuration object. If not provided, will create from environment.
        """
        self.config = config or PolarionConfig()
        self.config.validate()
        
        # Create session with retry strategy
        self.session = self._create_session()
        
        # Suppress SSL warnings if verification is disabled
        if not self.config.verify_ssl:
            warnings.filterwarnings('ignore', category=InsecureRequestWarning)
        
        # Set up logging
        if self.config.debug:
            logging.basicConfig(level=logging.DEBUG)
        
        logger.info(f"Initialized Polarion client for {self.config.base_url}")
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PATCH", "DELETE", "PUT"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update(self.config.get_headers())
        
        # SSL verification
        session.verify = self.config.verify_ssl
        
        return session
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Polarion API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            Various PolarionError subclasses based on response
        """
        # Build full URL
        url = urljoin(self.config.rest_api_url, endpoint.lstrip('/'))
        
        # Set timeout if not provided
        kwargs.setdefault('timeout', self.config.timeout)
        
        # Log request
        logger.debug(f"{method} {url}")
        if 'json' in kwargs:
            logger.debug(f"Request body: {kwargs['json']}")
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Log response
            logger.debug(f"Response status: {response.status_code}")
            if response.content:
                logger.debug(f"Response body: {response.text[:500]}...")
            
            # Handle response
            self._handle_response(response)
            
            return response
            
        except requests.exceptions.Timeout:
            raise PolarionTimeoutError(
                f"Request to {url} timed out after {kwargs.get('timeout')}s",
                timeout=kwargs.get('timeout')
            )
        except requests.exceptions.ConnectionError as e:
            raise PolarionConnectionError(
                f"Failed to connect to {url}: {str(e)}",
                url=url
            )
        except Exception as e:
            raise PolarionError(f"Unexpected error: {str(e)}")
    
    def _handle_response(self, response: requests.Response) -> None:
        """Handle API response and raise appropriate exceptions.
        
        Args:
            response: Response object
            
        Raises:
            Various PolarionError subclasses based on status code
        """
        # Success responses (2xx) and 204 No Content
        if 200 <= response.status_code < 300:
            return
        
        # Try to parse error response
        try:
            error_data = response.json() if response.content else {}
        except:
            error_data = {}
        
        # Handle specific error codes
        if response.status_code == 401:
            raise PolarionAuthError(response_data=error_data)
        
        elif response.status_code == 404:
            # Try to extract resource info from URL
            parts = response.url.split('/')
            resource_type = "Resource"
            resource_id = "unknown"
            
            if len(parts) >= 2:
                resource_type = parts[-2].rstrip('s')  # Remove plural 's'
                resource_id = parts[-1]
            
            raise PolarionNotFoundError(resource_type, resource_id, error_data)
        
        elif response.status_code == 400:
            # Extract validation errors
            validation_errors = []
            if "errors" in error_data:
                for error in error_data["errors"]:
                    if "detail" in error:
                        validation_errors.append(error["detail"])
            
            raise PolarionValidationError(
                validation_errors=validation_errors,
                response_data=error_data
            )
        
        elif 500 <= response.status_code < 600:
            raise PolarionServerError(
                f"Server error: {response.status_code}",
                status_code=response.status_code,
                response_data=error_data
            )
        
        else:
            # Generic error
            message = f"API request failed with status {response.status_code}"
            if error_data and "errors" in error_data and error_data["errors"]:
                error = error_data["errors"][0]
                if "detail" in error:
                    message = f"{message}: {error['detail']}"
            
            raise PolarionError(message, response.status_code, error_data)
    
    # Project methods
    
    def get_projects(self, **params) -> Dict[str, Any]:
        """Get all projects.
        
        Args:
            **params: Query parameters (page[size], page[number], sort, etc.)
            
        Returns:
            Projects collection response
        """
        query_string = build_query_params(params)
        endpoint = f"/projects{query_string}"
        
        response = self._request("GET", endpoint)
        return response.json()
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get a specific project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project resource
        """
        response = self._request("GET", f"/projects/{project_id}")
        return response.json()
    
    # Utility methods
    
    def test_connection(self) -> bool:
        """Test connection to Polarion API.
        
        Returns:
            True if connection successful
            
        Raises:
            PolarionError: If connection fails
        """
        try:
            self.get_projects(params={"page[size]": 1})
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close the client session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()