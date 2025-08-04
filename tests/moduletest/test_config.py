"""
Tests for the config module.
"""

import os
import pytest
from unittest.mock import patch
from polarion_api.config import PolarionConfig


class TestPolarionConfig:
    """Test the PolarionConfig class."""
    
    @pytest.mark.unit
    def test_default_config_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = PolarionConfig()
            
            # Check defaults
            assert config.base_url == "https://polarion.example.com"
            assert config.rest_path == "/polarion/rest/v1"
            assert config.api_path == "/polarion/api"
            assert config.verify_ssl is True
            assert config.timeout == 30
            assert config.max_retries == 3
            assert config.page_size == 100
            assert config.debug is False
    
    @pytest.mark.unit
    def test_config_from_environment(self):
        """Test loading configuration from environment variables."""
        test_env = {
            "POLARION_BASE_URL": "https://test.polarion.com",
            "POLARION_REST_V1_PATH": "/api/rest/v1",
            "POLARION_API_PATH": "/api/legacy",
            "POLARION_PERSONAL_ACCESS_TOKEN": "test-token-123",
            "POLARION_VERIFY_SSL": "false",
            "POLARION_TIMEOUT": "60",
            "POLARION_MAX_RETRIES": "5",
            "POLARION_DEFAULT_PROJECT_ID": "testproject",
            "POLARION_PAGE_SIZE": "50",
            "POLARION_DEBUG": "true"
        }
        
        with patch.dict(os.environ, test_env):
            config = PolarionConfig()
            
            assert config.base_url == "https://test.polarion.com"
            assert config.rest_path == "/api/rest/v1"
            assert config.api_path == "/api/legacy"
            assert config.personal_access_token == "test-token-123"
            assert config.verify_ssl is False
            assert config.timeout == 60
            assert config.max_retries == 5
            assert config.default_project_id == "testproject"
            assert config.page_size == 50
            assert config.debug is True
    
    @pytest.mark.unit
    def test_rest_api_url_property(self):
        """Test rest_api_url property."""
        with patch.dict(os.environ, {"POLARION_BASE_URL": "https://test.com"}):
            config = PolarionConfig()
            assert config.rest_api_url == "https://test.com/polarion/rest/v1"
    
    @pytest.mark.unit
    def test_legacy_api_url_property(self):
        """Test legacy_api_url property."""
        with patch.dict(os.environ, {"POLARION_BASE_URL": "https://test.com"}):
            config = PolarionConfig()
            assert config.legacy_api_url == "https://test.com/polarion/api"
    
    @pytest.mark.unit
    def test_base_url_trailing_slash_removal(self):
        """Test that trailing slashes are removed from base URL."""
        with patch.dict(os.environ, {"POLARION_BASE_URL": "https://test.com/"}):
            config = PolarionConfig()
            assert config.base_url == "https://test.com"
    
    @pytest.mark.unit
    def test_get_headers(self):
        """Test get_headers method."""
        with patch.dict(os.environ, {"POLARION_PERSONAL_ACCESS_TOKEN": "test-token"}):
            config = PolarionConfig()
            headers = config.get_headers()
            
            assert headers["Authorization"] == "Bearer test-token"
            assert headers["Accept"] == "*/*"
            assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.unit
    def test_validate_missing_base_url(self):
        """Test validation fails when base URL is missing."""
        with patch.dict(os.environ, {"POLARION_BASE_URL": ""}, clear=True):
            config = PolarionConfig()
            with pytest.raises(ValueError, match="POLARION_BASE_URL is required"):
                config.validate()
    
    @pytest.mark.unit
    def test_validate_missing_token(self):
        """Test validation fails when PAT is missing."""
        with patch.dict(os.environ, {"POLARION_PERSONAL_ACCESS_TOKEN": ""}, clear=True):
            config = PolarionConfig()
            with pytest.raises(ValueError, match="POLARION_PERSONAL_ACCESS_TOKEN is required"):
                config.validate()
    
    @pytest.mark.unit
    def test_validate_invalid_url_format(self):
        """Test validation fails for invalid URL format."""
        with patch.dict(os.environ, {
            "POLARION_BASE_URL": "not-a-url",
            "POLARION_PERSONAL_ACCESS_TOKEN": "token"
        }):
            config = PolarionConfig()
            with pytest.raises(ValueError, match="must start with http"):
                config.validate()
    
    @pytest.mark.unit
    def test_validate_invalid_timeout(self):
        """Test validation fails for invalid timeout."""
        with patch.dict(os.environ, {
            "POLARION_BASE_URL": "https://test.com",
            "POLARION_PERSONAL_ACCESS_TOKEN": "token",
            "POLARION_TIMEOUT": "0"
        }):
            config = PolarionConfig()
            with pytest.raises(ValueError, match="POLARION_TIMEOUT must be positive"):
                config.validate()
    
    @pytest.mark.unit
    def test_validate_invalid_retries(self):
        """Test validation fails for negative retries."""
        with patch.dict(os.environ, {
            "POLARION_BASE_URL": "https://test.com",
            "POLARION_PERSONAL_ACCESS_TOKEN": "token",
            "POLARION_MAX_RETRIES": "-1"
        }):
            config = PolarionConfig()
            with pytest.raises(ValueError, match="POLARION_MAX_RETRIES must be non-negative"):
                config.validate()
    
    @pytest.mark.unit
    def test_validate_invalid_page_size(self):
        """Test validation fails for invalid page size."""
        with patch.dict(os.environ, {
            "POLARION_BASE_URL": "https://test.com",
            "POLARION_PERSONAL_ACCESS_TOKEN": "token",
            "POLARION_PAGE_SIZE": "0"
        }):
            config = PolarionConfig()
            with pytest.raises(ValueError, match="POLARION_PAGE_SIZE must be positive"):
                config.validate()
    
    @pytest.mark.unit
    def test_validate_success(self):
        """Test successful validation."""
        with patch.dict(os.environ, {
            "POLARION_BASE_URL": "https://test.com",
            "POLARION_PERSONAL_ACCESS_TOKEN": "token"
        }):
            config = PolarionConfig()
            # Should not raise
            config.validate()
    
    @pytest.mark.unit
    def test_repr(self):
        """Test string representation."""
        with patch.dict(os.environ, {
            "POLARION_BASE_URL": "https://test.com",
            "POLARION_DEFAULT_PROJECT_ID": "myproject"
        }):
            config = PolarionConfig()
            repr_str = repr(config)
            
            assert "PolarionConfig" in repr_str
            assert "base_url='https://test.com'" in repr_str
            assert "default_project='myproject'" in repr_str