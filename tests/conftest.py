"""
Pytest configuration and shared fixtures for Polarion tests
"""

import os
import pytest
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Generator, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--env",
        action="store",
        default=os.getenv("POLARION_ENV", "mock"),
        choices=["mock", "production"],
        help="Target environment: mock or production"
    )
    parser.addoption(
        "--mock-url",
        action="store",
        default=os.getenv("MOCK_URL", "http://localhost:5000"),
        help="Mock server URL"
    )
    parser.addoption(
        "--polarion-endpoint",
        action="store",
        default=os.getenv("POLARION_API_ENDPOINT", "https://polarion.example.com/polarion/rest/v1"),
        help="Production Polarion REST API endpoint"
    )


@pytest.fixture(scope="session")
def test_env(request) -> str:
    """Get the test environment (mock or production)."""
    return request.config.getoption("--env")


@pytest.fixture(scope="session")
def base_url(request, test_env) -> str:
    """Get the base URL based on environment."""
    if test_env == "mock":
        return request.config.getoption("--mock-url")
    else:
        # For production, use the endpoint directly
        endpoint = request.config.getoption("--polarion-endpoint")
        # Extract base URL from endpoint (remove /rest/v1 part)
        return endpoint.replace("/polarion/rest/v1", "").replace("/rest/v1", "")


@pytest.fixture(scope="session")
def api_base_url(base_url, test_env) -> str:
    """Get the API base URL."""
    if test_env == "mock":
        return f"{base_url}/polarion/rest/v1"
    else:
        # For production, use the full endpoint
        return request.config.getoption("--polarion-endpoint")


@pytest.fixture(scope="session")
def auth_token(test_env) -> str:
    """Get authentication token based on environment."""
    if test_env == "mock":
        # For mock, use token from env or generate one
        mock_token = os.getenv("MOCK_AUTH_TOKEN")
        if mock_token:
            return mock_token
        # If auth is disabled, use dummy token
        if os.getenv('DISABLE_AUTH', 'false').lower() == 'true':
            return "mock-token-12345"
        # Otherwise generate a valid token
        from src.mock.middleware.auth import generate_mock_token
        return generate_mock_token("test-user")
    else:
        # For production, get Personal Access Token from environment variable
        token = os.getenv("POLARION_PERSONAL_ACCESS_TOKEN")
        if not token:
            pytest.skip("POLARION_PERSONAL_ACCESS_TOKEN not set for production testing")
        return token


@pytest.fixture
def auth_headers(auth_token, test_env) -> Dict[str, str]:
    """Get authorization headers."""
    # Check if we're testing against production Polarion
    if test_env == 'production':
        # Production Polarion requires wildcard Accept header
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "*/*"
        }
    else:
        # Mock server can handle standard JSON
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }


@pytest.fixture(scope="session")
def test_project_id() -> str:
    """Get test project ID."""
    return os.getenv("TEST_PROJECT_ID", "myproject")


@pytest.fixture(autouse=True)
def log_test_environment(request, test_logger):
    """Automatically log test environment for each test."""
    if request.node.name != 'test_logger':  # Avoid recursion
        env = request.config.getoption("--env")
        base_url = request.getfixturevalue('base_url') if 'base_url' in request.fixturenames else 'N/A'
        test_logger.debug(f"Test environment: {env}")
        test_logger.debug(f"Base URL: {base_url}")


@pytest.fixture
def mock_server_running(test_env, base_url, test_logger):
    """Ensure mock server is running when testing against mock."""
    if test_env == "mock":
        import requests
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code != 200:
                test_logger.error(f"Mock server not responding at {base_url}")
                pytest.skip("Mock server not responding at {base_url}")
            else:
                test_logger.info(f"Mock server is running at {base_url}")
        except requests.exceptions.RequestException as e:
            test_logger.error(f"Mock server not running at {base_url}: {str(e)}")
            pytest.skip(f"Mock server not running at {base_url}")


# Test markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "mock_only: test only runs against mock server")
    config.addinivalue_line("markers", "production_only: test only runs against production")
    config.addinivalue_line("markers", "smoke: basic smoke tests")
    config.addinivalue_line("markers", "integration: integration tests")


# Skip tests based on environment
def pytest_collection_modifyitems(config, items):
    """Skip tests based on environment."""
    env = config.getoption("--env")
    
    skip_mock = pytest.mark.skip(reason="Test only for production environment")
    skip_prod = pytest.mark.skip(reason="Test only for mock environment")
    
    for item in items:
        if env == "mock" and "production_only" in item.keywords:
            item.add_marker(skip_mock)
        elif env == "production" and "mock_only" in item.keywords:
            item.add_marker(skip_prod)


@pytest.fixture(scope="session")
def test_logger(request):
    """Create a logger for test session."""
    # Get test session info
    test_name = request.node.name if hasattr(request.node, 'name') else 'test_session'
    test_file = request.node.parent.name if hasattr(request.node, 'parent') and request.node.parent else 'session'
    
    # Create logger
    test_logger = logging.getLogger(f"tests.{test_file}")
    test_logger.setLevel(logging.DEBUG)
    
    # Add file handler if not already present
    if not test_logger.handlers:
        # Create logs directory if it doesn't exist
        log_dir = Path("test_logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"test_session_{timestamp}.log"
        
        # Configure file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        test_logger.addHandler(file_handler)
        
        # Log session start
        test_logger.info("=" * 80)
        test_logger.info(f"Test Session Started: {timestamp}")
        test_logger.info(f"Environment: {os.getenv('POLARION_ENV', 'mock')}")
        test_logger.info("=" * 80)
    
    return test_logger


@pytest.fixture
def log_test_info(request, test_logger):
    """Log test information at the start and end of each test."""
    test_name = request.node.name
    test_file = request.node.parent.name if hasattr(request.node, 'parent') and request.node.parent else 'unknown'
    
    # Log test start
    test_logger.info(f"\n{'='*60}")
    test_logger.info(f"TEST START: {test_name}")
    test_logger.info(f"File: {test_file}")
    test_logger.info(f"Time: {datetime.now()}")
    test_logger.info(f"{'='*60}\n")
    
    yield test_logger
    
    # Log test end
    test_logger.info(f"\n{'='*60}")
    test_logger.info(f"TEST END: {test_name}")
    test_logger.info(f"{'='*60}\n")


@pytest.fixture
def capture_api_calls(test_logger):
    """Fixture to capture and log API calls."""
    api_calls = []
    
    def log_api_call(method, url, status_code, response_time=None, request_data=None, response_data=None):
        """Log an API call."""
        call_info = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url": url,
            "status_code": status_code,
            "response_time": response_time,
            "request_data": request_data,
            "response_data": response_data
        }
        api_calls.append(call_info)
        
        # Log to file
        test_logger.debug(f"API Call: {method} {url} -> {status_code}")
        if request_data:
            test_logger.debug(f"Request: {json.dumps(request_data, indent=2)}")
        if response_data:
            test_logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
    
    yield log_api_call
    
    # Summary at the end
    if api_calls:
        test_logger.info(f"Total API calls in test: {len(api_calls)}")
        for call in api_calls:
            test_logger.info(f"  - {call['method']} {call['url']} -> {call['status_code']}")