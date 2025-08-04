"""
Tests for the client module.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from polarion_api import PolarionClient
from polarion_api.config import PolarionConfig
from polarion_api.exceptions import (
    PolarionError,
    PolarionAuthError,
    PolarionNotFoundError,
    PolarionValidationError,
    PolarionServerError,
    PolarionTimeoutError,
    PolarionConnectionError
)


class TestPolarionClient:
    """Test the PolarionClient class."""
    
    @pytest.mark.unit
    def test_client_initialization(self):
        """Test client initialization with config."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            assert client.config == config
    
    @pytest.mark.unit
    def test_client_initialization_without_config(self):
        """Test client initialization without config (uses defaults)."""
        with patch('polarion_api.config.PolarionConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.validate.return_value = None
            mock_config_class.return_value = mock_config
            
            with patch('polarion_api.client.PolarionClient._create_session'):
                client = PolarionClient()
                assert client.config == mock_config
                mock_config.validate.assert_called_once()
    
    @pytest.mark.unit
    def test_create_session(self):
        """Test session creation with retry strategy."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        config.max_retries = 3
        config.verify_ssl = False
        
        client = PolarionClient(config=config)
        
        # Check session properties
        assert isinstance(client.session, requests.Session)
        assert client.session.verify is False
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test-token"
    
    @pytest.mark.unit
    def test_request_success(self):
        """Test successful request."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        config.rest_api_url = "https://test.com/api"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            # Mock session
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_response.content = b'{"data": "test"}'
            mock_response.text = '{"data": "test"}'
            
            client.session = Mock()
            client.session.request.return_value = mock_response
            
            response = client._request("GET", "/test")
            
            assert response == mock_response
            client.session.request.assert_called_once()
    
    @pytest.mark.unit
    def test_request_auth_error(self):
        """Test request with authentication error."""
        config = PolarionConfig()
        config.personal_access_token = "invalid-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            # Mock 401 response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"errors": [{"status": "401", "detail": "Unauthorized"}]}
            mock_response.content = b'{"errors": [{"status": "401"}]}'
            
            client.session = Mock()
            client.session.request.return_value = mock_response
            
            with pytest.raises(PolarionAuthError):
                client._request("GET", "/test")
    
    @pytest.mark.unit
    def test_request_not_found_error(self):
        """Test request with not found error."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.url = "https://test.com/api/projects/myproject/workitems/123"
            mock_response.json.return_value = {"errors": [{"status": "404"}]}
            mock_response.content = b'{"errors": [{"status": "404"}]}'
            
            client.session = Mock()
            client.session.request.return_value = mock_response
            
            with pytest.raises(PolarionNotFoundError) as exc_info:
                client._request("GET", "/test")
            
            assert exc_info.value.resource_type == "workitem"
            assert exc_info.value.resource_id == "123"
    
    @pytest.mark.unit
    def test_request_validation_error(self):
        """Test request with validation error."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            # Mock 400 response
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": [
                    {"status": "400", "detail": "Invalid field: title"},
                    {"status": "400", "detail": "Missing required field: type"}
                ]
            }
            mock_response.content = b'{"errors": []}'
            
            client.session = Mock()
            client.session.request.return_value = mock_response
            
            with pytest.raises(PolarionValidationError) as exc_info:
                client._request("POST", "/test")
            
            assert len(exc_info.value.validation_errors) == 2
    
    @pytest.mark.unit
    def test_request_server_error(self):
        """Test request with server error."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            # Mock 500 response
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"errors": [{"status": "500"}]}
            mock_response.content = b'{"errors": []}'
            
            client.session = Mock()
            client.session.request.return_value = mock_response
            
            with pytest.raises(PolarionServerError) as exc_info:
                client._request("GET", "/test")
            
            assert exc_info.value.status_code == 500
    
    @pytest.mark.unit
    def test_request_timeout(self):
        """Test request timeout."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        config.timeout = 5
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            client.session = Mock()
            client.session.request.side_effect = requests.exceptions.Timeout()
            
            with pytest.raises(PolarionTimeoutError) as exc_info:
                client._request("GET", "/test")
            
            assert exc_info.value.timeout == 5
    
    @pytest.mark.unit
    def test_request_connection_error(self):
        """Test request connection error."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            client.session = Mock()
            client.session.request.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            with pytest.raises(PolarionConnectionError):
                client._request("GET", "/test")
    
    @pytest.mark.integration
    def test_get_projects(self, polarion_client):
        """Test getting projects."""
        projects = polarion_client.get_projects()
        
        assert "data" in projects
        assert isinstance(projects["data"], list)
        
        if projects["data"]:
            project = projects["data"][0]
            assert "type" in project
            assert project["type"] == "projects"
            assert "id" in project
            assert "attributes" in project
    
    @pytest.mark.integration
    def test_get_project(self, polarion_client, test_project_id):
        """Test getting a specific project."""
        try:
            project = polarion_client.get_project(test_project_id)
            
            assert "data" in project
            assert project["data"]["id"] == test_project_id
            assert project["data"]["type"] == "projects"
        except PolarionNotFoundError:
            pytest.skip(f"Test project '{test_project_id}' not found")
    
    @pytest.mark.integration
    def test_test_connection_success(self, polarion_client):
        """Test connection test method."""
        # Should return True if connection successful
        assert polarion_client.test_connection() is True
    
    @pytest.mark.unit
    def test_test_connection_failure(self):
        """Test connection test method with failure."""
        config = PolarionConfig()
        config.personal_access_token = "invalid-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            
            # Mock failed response
            client.session = Mock()
            client.session.request.side_effect = PolarionAuthError()
            
            with pytest.raises(PolarionAuthError):
                client.test_connection()
    
    @pytest.mark.unit
    def test_context_manager(self):
        """Test client as context manager."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            with patch('polarion_api.client.PolarionClient.close') as mock_close:
                with PolarionClient(config=config) as client:
                    assert isinstance(client, PolarionClient)
                
                mock_close.assert_called_once()
    
    @pytest.mark.unit
    def test_close(self):
        """Test closing the client."""
        config = PolarionConfig()
        config.personal_access_token = "test-token"
        
        with patch('polarion_api.client.PolarionClient._create_session'):
            client = PolarionClient(config=config)
            client.session = Mock()
            
            client.close()
            client.session.close.assert_called_once()