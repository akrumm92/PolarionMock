"""
Test helpers and utilities for Polarion Mock tests.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class APITestClient:
    """Helper class for API testing."""
    
    def __init__(self, base_url: str, headers: Dict[str, str]):
        self.base_url = base_url
        self.headers = headers
    
    def get(self, endpoint: str, **kwargs) -> Any:
        """Make GET request."""
        # This is a placeholder - actual implementation would use requests
        pass
    
    def post(self, endpoint: str, data: Any, **kwargs) -> Any:
        """Make POST request."""
        pass
    
    def patch(self, endpoint: str, data: Any, **kwargs) -> Any:
        """Make PATCH request."""
        pass
    
    def delete(self, endpoint: str, **kwargs) -> Any:
        """Make DELETE request."""
        pass


def log_test_data(test_name: str, data: Any, description: str = "") -> None:
    """Log test data for debugging."""
    timestamp = datetime.now().isoformat()
    logger.info(f"[{timestamp}] Test: {test_name}")
    if description:
        logger.info(f"Description: {description}")
    
    if isinstance(data, (dict, list)):
        logger.info(f"Data: {json.dumps(data, indent=2)}")
    else:
        logger.info(f"Data: {data}")


def assert_with_logging(condition: bool, message: str, data: Any = None) -> None:
    """Assert with additional logging."""
    if not condition:
        logger.error(f"Assertion failed: {message}")
        if data:
            logger.error(f"Data: {json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data}")
    assert condition, message


def log_test_section(section_name: str) -> None:
    """Log test section separator."""
    separator = "=" * 80
    logger.info(f"\n{separator}")
    logger.info(f"{section_name}")
    logger.info(f"{separator}\n")


def compare_responses(expected: Dict[str, Any], actual: Dict[str, Any], 
                     ignore_fields: Optional[List[str]] = None) -> bool:
    """Compare two API responses, optionally ignoring certain fields."""
    ignore_fields = ignore_fields or []
    
    def clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """Remove ignored fields from dict."""
        cleaned = {}
        for k, v in d.items():
            if k not in ignore_fields:
                if isinstance(v, dict):
                    cleaned[k] = clean_dict(v)
                elif isinstance(v, list):
                    cleaned[k] = [clean_dict(item) if isinstance(item, dict) else item for item in v]
                else:
                    cleaned[k] = v
        return cleaned
    
    cleaned_expected = clean_dict(expected)
    cleaned_actual = clean_dict(actual)
    
    return cleaned_expected == cleaned_actual


def extract_error_details(response: Any) -> Optional[str]:
    """Extract error details from response."""
    try:
        if hasattr(response, 'json'):
            data = response.json()
            if 'errors' in data and data['errors']:
                error = data['errors'][0]
                return f"{error.get('title', 'Unknown')}: {error.get('detail', 'No details')}"
        return None
    except:
        return None