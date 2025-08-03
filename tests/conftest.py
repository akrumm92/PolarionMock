"""
Pytest configuration and shared fixtures for Polarion tests
"""

import os
import pytest
import logging
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
        "--polarion-url",
        action="store",
        default=os.getenv("POLARION_API_URL", "https://polarion.example.com"),
        help="Production Polarion URL"
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
        return request.config.getoption("--polarion-url")


@pytest.fixture(scope="session")
def api_base_url(base_url, test_env) -> str:
    """Get the API base URL."""
    if test_env == "mock":
        return f"{base_url}/polarion/rest/v1"
    else:
        return f"{base_url}/rest/v1"


@pytest.fixture(scope="session")
def auth_token(test_env) -> str:
    """Get authentication token based on environment."""
    if test_env == "mock":
        # For mock, we can use a simple token or generate one
        return "mock-token-12345"
    else:
        # For production, get from environment variable
        token = os.getenv("POLARION_API_TOKEN")
        if not token:
            pytest.skip("POLARION_API_TOKEN not set for production testing")
        return token


@pytest.fixture
def auth_headers(auth_token) -> Dict[str, str]:
    """Get authorization headers."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


@pytest.fixture(scope="session")
def test_project_id() -> str:
    """Get test project ID."""
    return os.getenv("TEST_PROJECT_ID", "myproject")


@pytest.fixture
def mock_server_running(test_env, base_url):
    """Ensure mock server is running when testing against mock."""
    if test_env == "mock":
        import requests
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code != 200:
                pytest.skip("Mock server not responding at {base_url}")
        except requests.exceptions.RequestException:
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