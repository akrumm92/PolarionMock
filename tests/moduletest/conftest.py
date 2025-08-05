"""
Shared pytest fixtures for polarion_api module tests.
"""

import os
import pytest
import logging
from datetime import datetime
from typing import Generator, Optional
from dotenv import load_dotenv

# Add src to Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from polarion_api import PolarionClient
from polarion_api.config import PolarionConfig

# Load environment variables
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger = logging.getLogger(__name__)
    logger.debug(f"Loaded .env from {env_path}")
else:
    load_dotenv()  # Try to load from current directory
    logger = logging.getLogger(__name__)
    logger.warning(f"No .env file found at {env_path}, using system environment")

# Configure logging
logging.basicConfig(level=logging.INFO)


@pytest.fixture(scope="session")
def test_env(request) -> str:
    """Get the test environment (mock or production)."""
    return os.getenv("POLARION_ENV", "mock")


@pytest.fixture(scope="session")
def test_config() -> PolarionConfig:
    """Create test configuration."""
    config = PolarionConfig()
    
    # Override for testing if needed
    if os.getenv("POLARION_ENV") == "mock":
        config.base_url = os.getenv("MOCK_URL", "http://localhost:5001")
        config.personal_access_token = os.getenv("MOCK_AUTH_TOKEN", "test-token")
    
    return config


@pytest.fixture
def polarion_client(test_config) -> Generator[PolarionClient, None, None]:
    """Create Polarion client for testing."""
    client = PolarionClient(config=test_config)
    yield client
    client.close()


@pytest.fixture(scope="session")
def test_project_id() -> str:
    """Get test project ID."""
    # Always check environment variable first
    env_project_id = os.getenv("TEST_PROJECT_ID")
    
    if env_project_id:
        return env_project_id
    
    # For production, try to load from config file
    if os.getenv("POLARION_ENV") == "production":
        try:
            from .test_config_production import PRODUCTION_PROJECTS
            return PRODUCTION_PROJECTS.get("default", "myproject")
        except ImportError:
            # If no TEST_PROJECT_ID is set in production, skip the test
            pytest.skip("TEST_PROJECT_ID environment variable not set for production testing")
    
    # Default for mock environment
    return "myproject"


@pytest.fixture
def unique_suffix() -> str:
    """Generate unique suffix for test data."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]


@pytest.fixture
def test_work_item_data(unique_suffix) -> dict:
    """Generate test work item data."""
    return {
        "title": f"Test Work Item {unique_suffix}",
        "work_item_type": "requirement",
        "description": {
            "type": "text/html",
            "value": f"<p>Test work item created at {unique_suffix}</p>"
        },
        "status": "open",
        "priority": "high",
        "severity": "major"
    }


@pytest.fixture
def test_document_data(unique_suffix) -> dict:
    """Generate test document data."""
    return {
        "module_name": f"test_doc_{unique_suffix}",
        "title": f"Test Document {unique_suffix}",
        "document_type": "req_specification",
        "home_page_content": {
            "type": "text/html",
            "value": f"<h1>Test Document</h1><p>Created at {unique_suffix}</p>"
        }
    }


@pytest.fixture
def created_work_items(polarion_client) -> Generator[list, None, None]:
    """Track created work items for cleanup."""
    items = []
    yield items
    
    # Cleanup
    for item_id in items:
        try:
            polarion_client.delete_work_item(item_id)
            logger.info(f"Cleaned up work item: {item_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up work item {item_id}: {e}")


@pytest.fixture
def created_documents(polarion_client) -> Generator[list, None, None]:
    """Track created documents for cleanup."""
    docs = []
    yield docs
    
    # Cleanup
    for doc_id in docs:
        try:
            polarion_client.delete_document(doc_id)
            logger.info(f"Cleaned up document: {doc_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up document {doc_id}: {e}")


# Skip markers based on environment
def pytest_collection_modifyitems(config, items):
    """Skip tests based on environment."""
    env = os.getenv("POLARION_ENV", "mock")
    allow_destructive = os.getenv("ALLOW_DESTRUCTIVE_TESTS", "false").lower() == "true"
    
    skip_mock = pytest.mark.skip(reason="Test only for production environment")
    skip_prod = pytest.mark.skip(reason="Test only for mock environment")
    skip_destructive = pytest.mark.skip(reason="Destructive tests not allowed in production (set ALLOW_DESTRUCTIVE_TESTS=true to enable)")
    
    for item in items:
        if env == "mock" and "production_only" in item.keywords:
            item.add_marker(skip_mock)
        elif env == "production" and "mock_only" in item.keywords:
            item.add_marker(skip_prod)
        elif env == "production" and "destructive" in item.keywords and not allow_destructive:
            item.add_marker(skip_destructive)


@pytest.fixture
def test_document_id(test_env):
    """Get test document ID based on environment."""
    if test_env == "production":
        # Use environment variable or skip test
        doc_id = os.getenv("TEST_DOCUMENT_ID")
        if not doc_id:
            pytest.skip("TEST_DOCUMENT_ID not set for production testing")
        return doc_id
    else:
        # Mock environment - use default test data
        return "elibrary/_default/requirements"


@pytest.fixture  
def test_work_item_id(test_env, test_project_id):
    """Get test work item ID based on environment."""
    if test_env == "production":
        # Use environment variable or skip test
        wi_id = os.getenv("TEST_WORK_ITEM_ID")
        if not wi_id:
            pytest.skip("TEST_WORK_ITEM_ID not set for production testing")
        return wi_id
    else:
        # Mock environment - use default test data
        return f"{test_project_id}/WI-001"


# Custom markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "mock_only: test only runs against mock server")
    config.addinivalue_line("markers", "production_only: test only runs against production")
    config.addinivalue_line("markers", "integration: integration tests requiring API access")
    config.addinivalue_line("markers", "unit: unit tests not requiring API access")
    config.addinivalue_line("markers", "destructive: tests that create, update, or delete resources")