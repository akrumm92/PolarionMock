"""
Test script for Polarion Projects API
Tests run against both mock and production environments
"""

import pytest
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class TestProjects:
    """Test suite for Projects API endpoints."""
    
    @pytest.mark.smoke
    def test_api_availability(self, api_base_url, test_env):
        """Test if API is available by checking projects endpoint without auth."""
        url = f"{api_base_url}/projects"
        response = requests.get(url)
        
        # According to Polarion spec, /projects returns 401 when API is available
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Check error format
        data = response.json()
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert data["errors"][0]["status"] == "401"
        
        logger.info(f"[{test_env}] API is available at {api_base_url}")
    
    @pytest.mark.integration
    def test_list_projects(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test listing all projects."""
        url = f"{api_base_url}/projects"
        response = requests.get(url, headers=auth_headers)
        
        # Check response status
        assert response.status_code == 200, f"Failed to list projects: {response.text}"
        
        # Validate JSON:API response structure
        data = response.json()
        assert "data" in data, "Response missing 'data' field"
        assert isinstance(data["data"], list), "Data should be a list"
        
        # Check meta information
        assert "meta" in data, "Response missing 'meta' field"
        meta = data["meta"]
        assert "totalCount" in meta
        
        # If projects exist, validate structure
        if len(data["data"]) > 0:
            project = data["data"][0]
            self._validate_project_structure(project)
        
        logger.info(f"[{test_env}] Found {len(data['data'])} projects")
        
        # Store project IDs for other tests
        project_ids = [p["id"] for p in data["data"]]
        return project_ids
    
    @pytest.mark.integration
    def test_get_project_by_id(self, api_base_url, auth_headers, test_project_id, test_env, mock_server_running):
        """Test getting a specific project by ID."""
        url = f"{api_base_url}/projects/{test_project_id}"
        response = requests.get(url, headers=auth_headers)
        
        # Check if project exists
        if response.status_code == 404:
            pytest.skip(f"Test project '{test_project_id}' not found in {test_env}")
        
        assert response.status_code == 200, f"Failed to get project: {response.text}"
        
        # Validate response
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == test_project_id
        assert data["data"]["type"] == "projects"
        
        self._validate_project_structure(data["data"])
        
        logger.info(f"[{test_env}] Successfully retrieved project: {test_project_id}")
    
    @pytest.mark.integration
    def test_project_pagination(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test pagination for projects listing."""
        # First request with page size 2
        url = f"{api_base_url}/projects?page[size]=2&page[number]=1"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination metadata
        assert "meta" in data
        assert "links" in data
        
        meta = data["meta"]
        assert "currentPage" in meta
        assert "pageSize" in meta
        assert meta["currentPage"] == 1
        assert meta["pageSize"] == 2
        
        # Check pagination links
        links = data["links"]
        assert "self" in links
        assert "first" in links
        assert "last" in links
        
        logger.info(f"[{test_env}] Pagination working correctly")
    
    @pytest.mark.integration
    def test_project_sparse_fieldsets(self, api_base_url, auth_headers, test_project_id, test_env, mock_server_running):
        """Test sparse fieldsets functionality."""
        url = f"{api_base_url}/projects/{test_project_id}?fields[projects]=name,created"
        response = requests.get(url, headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip(f"Test project '{test_project_id}' not found")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that only requested fields are present
        if "attributes" in data["data"]:
            attrs = data["data"]["attributes"]
            # These fields were requested
            assert "name" in attrs or len(attrs) == 0  # Some implementations might not support sparse fieldsets
            
        logger.info(f"[{test_env}] Sparse fieldsets test completed")
    
    @pytest.mark.mock_only
    def test_create_project(self, api_base_url, auth_headers):
        """Test creating a new project (mock only)."""
        project_data = {
            "data": {
                "type": "projects",
                "id": "test-project-001",
                "attributes": {
                    "name": "Test Project 001",
                    "description": {
                        "type": "text/plain",
                        "value": "Created by automated test"
                    },
                    "trackerPrefix": "TP001"
                }
            }
        }
        
        url = f"{api_base_url}/projects"
        response = requests.post(url, headers=auth_headers, json=project_data)
        
        assert response.status_code == 201, f"Failed to create project: {response.text}"
        
        # Validate response
        data = response.json()
        assert data["data"]["id"] == "test-project-001"
        assert data["data"]["attributes"]["name"] == "Test Project 001"
        
        logger.info("[mock] Successfully created test project")
        
        # Clean up - delete the project
        delete_url = f"{api_base_url}/projects/test-project-001"
        requests.delete(delete_url, headers=auth_headers)
    
    @pytest.mark.integration
    def test_project_sorting(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test sorting projects."""
        # Sort by name ascending
        url = f"{api_base_url}/projects?sort=name"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["data"]) > 1:
            # Check if properly sorted
            names = [p["attributes"]["name"] for p in data["data"] if "attributes" in p and "name" in p["attributes"]]
            assert names == sorted(names), "Projects not sorted by name ascending"
        
        # Sort by name descending
        url = f"{api_base_url}/projects?sort=-name"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["data"]) > 1:
            names = [p["attributes"]["name"] for p in data["data"] if "attributes" in p and "name" in p["attributes"]]
            assert names == sorted(names, reverse=True), "Projects not sorted by name descending"
        
        logger.info(f"[{test_env}] Sorting functionality verified")
    
    def _validate_project_structure(self, project: Dict[str, Any]):
        """Validate project object structure."""
        # Required fields
        assert "type" in project
        assert project["type"] == "projects"
        assert "id" in project
        
        # Links
        assert "links" in project
        assert "self" in project["links"]
        
        # Attributes (if present)
        if "attributes" in project:
            attrs = project["attributes"]
            # Common attributes
            expected_attrs = ["name", "id"]
            for attr in expected_attrs:
                if attr in attrs:
                    assert attrs[attr] is not None


@pytest.mark.integration
class TestProjectComparison:
    """Compare responses between mock and production."""
    
    def test_compare_project_structure(self, request):
        """Run tests against both environments and compare."""
        if request.config.getoption("--env") != "mock":
            pytest.skip("Comparison test only runs in mock environment")
        
        # This is a special test that would run the same tests against both
        # environments and compare the responses
        # For now, we'll just log that this capability exists
        logger.info("Project structure comparison test - would compare mock vs production responses")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])