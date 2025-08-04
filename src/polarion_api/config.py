"""
Configuration module for Polarion API client.

Loads configuration from environment variables using python-dotenv.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


class PolarionConfig:
    """Configuration for Polarion API client."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Polarion connection settings
        self.base_url = os.getenv("POLARION_BASE_URL", "https://polarion.example.com").rstrip("/")
        self.rest_path = os.getenv("POLARION_REST_V1_PATH", "/polarion/rest/v1")
        self.api_path = os.getenv("POLARION_API_PATH", "/polarion/api")
        
        # Authentication
        self.personal_access_token = os.getenv("POLARION_PERSONAL_ACCESS_TOKEN")
        
        # SSL verification
        self.verify_ssl = os.getenv("POLARION_VERIFY_SSL", "true").lower() == "true"
        
        # Request settings
        self.timeout = int(os.getenv("POLARION_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("POLARION_MAX_RETRIES", "3"))
        
        # Default project (optional)
        self.default_project_id = os.getenv("POLARION_DEFAULT_PROJECT_ID")
        
        # Performance settings
        self.page_size = int(os.getenv("POLARION_PAGE_SIZE", "100"))
        
        # Logging
        self.debug = os.getenv("POLARION_DEBUG", "false").lower() == "true"
    
    @property
    def rest_api_url(self) -> str:
        """Get full REST API v1 URL."""
        return f"{self.base_url}{self.rest_path}"
    
    @property
    def legacy_api_url(self) -> str:
        """Get full legacy API URL."""
        return f"{self.base_url}{self.api_path}"
    
    def validate(self) -> None:
        """Validate configuration.
        
        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        if not self.base_url:
            raise ValueError("POLARION_BASE_URL is required")
        
        if not self.personal_access_token:
            raise ValueError("POLARION_PERSONAL_ACCESS_TOKEN is required")
        
        # Validate URL format
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("POLARION_BASE_URL must start with http:// or https://")
        
        # Validate numeric values
        if self.timeout <= 0:
            raise ValueError("POLARION_TIMEOUT must be positive")
        
        if self.max_retries < 0:
            raise ValueError("POLARION_MAX_RETRIES must be non-negative")
        
        if self.page_size <= 0:
            raise ValueError("POLARION_PAGE_SIZE must be positive")
    
    def get_headers(self) -> dict:
        """Get default headers for API requests.
        
        Returns:
            dict: Headers with authorization and content type.
        """
        return {
            "Authorization": f"Bearer {self.personal_access_token}",
            "Accept": "*/*",  # MUST use wildcard - Polarion returns 406 with other values!
            "Content-Type": "application/json"
        }
    
    def __repr__(self) -> str:
        """String representation of config."""
        return (
            f"PolarionConfig("
            f"base_url='{self.base_url}', "
            f"verify_ssl={self.verify_ssl}, "
            f"timeout={self.timeout}s, "
            f"default_project='{self.default_project_id or 'None'}')"
        )


# Create a default config instance
default_config = PolarionConfig()