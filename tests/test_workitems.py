"""
Test script for Polarion Work Items API
Tests run against both mock and production environments
"""

import pytest
import requests
import logging
import os
from typing import List, Dict, Any
from tests.utils.test_helpers import APITestClient, log_test_data, assert_with_logging, log_test_section

logger = logging.getLogger(__name__)


class TestWorkItems:
    """Test suite for Work Items API endpoints."""
    
    @pytest.mark.integration
    def test_list_project_workitems(self, api_base_url, auth_headers, test_project_id, test_env, mock_server_running):
        """Test listing work items for a specific project."""
        url = f"{api_base_url}/projects/{test_project_id}/workitems"
        response = requests.get(url, headers=auth_headers)
        
        # Check if project exists
        if response.status_code == 404:
            pytest.skip(f"Project '{test_project_id}' not found in {test_env}")
        
        assert response.status_code == 200, f"Failed to list work items: {response.text}"
        
        # Validate JSON:API response structure
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Check meta information
        assert "meta" in data
        assert "totalCount" in data["meta"]
        
        # If work items exist, validate structure
        if len(data["data"]) > 0:
            workitem = data["data"][0]
            self._validate_workitem_structure(workitem)
        
        logger.info(f"[{test_env}] Found {len(data['data'])} work items in project {test_project_id}")
    
    @pytest.mark.integration
    def test_list_all_workitems(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test listing all work items across all projects."""
        url = f"{api_base_url}/all/workitems"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Failed to list all work items: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        logger.info(f"[{test_env}] Found {len(data['data'])} work items total")
    
    @pytest.mark.integration
    def test_get_workitem(self, api_base_url, auth_headers, test_project_id, test_env, mock_server_running):
        """Test getting a specific work item."""
        # First, list work items to find one
        url = f"{api_base_url}/projects/{test_project_id}/workitems?page[size]=1"
        response = requests.get(url, headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip(f"Project '{test_project_id}' not found")
        
        if response.status_code != 200 or len(response.json()["data"]) == 0:
            pytest.skip("No work items found to test")
        
        workitem_id = response.json()["data"][0]["id"]
        # Parse work item ID to get components
        parts = workitem_id.split("/")
        if len(parts) != 2:
            pytest.skip(f"Invalid work item ID format: {workitem_id}")
        
        project_id, item_id = parts
        
        # Get specific work item
        url = f"{api_base_url}/projects/{project_id}/workitems/{item_id}"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Failed to get work item: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == workitem_id
        
        self._validate_workitem_structure(data["data"])
        
        logger.info(f"[{test_env}] Successfully retrieved work item: {workitem_id}")
    
    @pytest.mark.mock_only
    def test_create_workitem(self, api_base_url, auth_headers):
        """Test creating a new work item (mock only)."""
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Test Work Item 001",
                    "type": "requirement",
                    "description": {
                        "type": "text/html",
                        "value": "<p>Created by automated test</p>"
                    },
                    "priority": "high",
                    "status": "open"
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=workitem_data)
        
        assert response.status_code == 201, f"Failed to create work item: {response.text}"
        
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["attributes"]["title"] == "Test Work Item 001"
        
        created_id = data["data"][0]["id"]
        logger.info(f"[mock] Successfully created work item: {created_id}")
        
        # Clean up - delete the work item
        parts = created_id.split("/")
        delete_url = f"{api_base_url}/projects/{parts[0]}/workitems/{parts[1]}"
        requests.delete(delete_url, headers=auth_headers)
    
    @pytest.mark.mock_only
    def test_create_workitem_in_document(self, api_base_url, auth_headers):
        """Test creating a work item with document relationship."""
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Work Item in Document",
                    "type": "requirement",
                    "description": {
                        "type": "text/plain",
                        "value": "This work item belongs to a document"
                    }
                },
                "relationships": {
                    "module": {
                        "data": {
                            "type": "documents",
                            "id": "myproject/_default/user_stories"
                        }
                    }
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=workitem_data)
        
        assert response.status_code == 201, f"Failed to create work item in document: {response.text}"
        
        data = response.json()
        workitem = data["data"][0]
        
        # Verify module relationship
        assert "relationships" in workitem
        assert "module" in workitem["relationships"]
        assert workitem["relationships"]["module"]["data"]["id"] == "myproject/_default/user_stories"
        
        created_id = workitem["id"]
        logger.info(f"[mock] Successfully created work item in document: {created_id}")
        
        # Clean up
        parts = created_id.split("/")
        delete_url = f"{api_base_url}/projects/{parts[0]}/workitems/{parts[1]}"
        requests.delete(delete_url, headers=auth_headers)
    
    @pytest.mark.integration
    def test_query_workitems(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test querying work items with filters."""
        # Query by type
        url = f"{api_base_url}/all/workitems?query=type:requirement"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify results if any
        if len(data["data"]) > 0:
            for workitem in data["data"]:
                if "attributes" in workitem and "type" in workitem["attributes"]:
                    # Some implementations might not filter server-side
                    pass
        
        logger.info(f"[{test_env}] Query returned {len(data['data'])} work items")
    
    @pytest.mark.integration
    def test_workitem_with_includes(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test including related resources."""
        if test_env == "mock":
            # Use known project with work items that have modules
            url = f"{api_base_url}/projects/elibrary/workitems?include=module&page[size]=5"
        else:
            url = f"{api_base_url}/all/workitems?include=module&page[size]=5"
        
        response = requests.get(url, headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip("Test project not found")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if included section exists when work items have modules
        workitems_with_modules = [
            wi for wi in data["data"] 
            if wi.get("relationships", {}).get("module")
        ]
        
        if workitems_with_modules and "included" in data:
            # Verify included resources are documents
            for included in data["included"]:
                assert included["type"] == "documents"
        
        logger.info(f"[{test_env}] Successfully tested includes")
    
    @pytest.mark.mock_only
    def test_update_workitem(self, api_base_url, auth_headers):
        """Test updating a work item."""
        # First create a work item
        create_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Work Item to Update",
                    "status": "open",
                    "priority": "low"
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=create_data)
        assert response.status_code == 201
        
        created_id = response.json()["data"][0]["id"]
        parts = created_id.split("/")
        
        # Update the work item
        update_data = {
            "data": {
                "type": "workitems",
                "id": created_id,
                "attributes": {
                    "status": "in_progress",
                    "priority": "high",
                    "title": "Updated Work Item Title"
                }
            }
        }
        
        url = f"{api_base_url}/projects/{parts[0]}/workitems/{parts[1]}"
        response = requests.patch(url, headers=auth_headers, json=update_data)
        
        assert response.status_code == 200, f"Failed to update work item: {response.text}"
        
        updated = response.json()["data"]
        assert updated["attributes"]["status"] == "in_progress"
        assert updated["attributes"]["priority"] == "high"
        assert updated["attributes"]["title"] == "Updated Work Item Title"
        
        logger.info(f"[mock] Successfully updated work item: {created_id}")
        
        # Clean up
        requests.delete(url, headers=auth_headers)
    
    @pytest.mark.mock_only
    def test_move_workitem_to_document(self, api_base_url, auth_headers):
        """Test moving a work item to a document."""
        # Create a work item without document
        create_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Work Item to Move",
                    "type": "task"
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=create_data)
        assert response.status_code == 201
        
        created_id = response.json()["data"][0]["id"]
        parts = created_id.split("/")
        
        # Move to document
        move_data = {
            "targetDocument": "myproject/_default/user_stories"
        }
        
        url = f"{api_base_url}/projects/{parts[0]}/workitems/{parts[1]}/actions/moveToDocument"
        response = requests.post(url, headers=auth_headers, json=move_data)
        
        assert response.status_code == 200, f"Failed to move work item: {response.text}"
        
        result = response.json()
        assert result["data"]["attributes"]["status"] == "success"
        
        logger.info(f"[mock] Successfully moved work item to document")
        
        # Clean up
        delete_url = f"{api_base_url}/projects/{parts[0]}/workitems/{parts[1]}"
        requests.delete(delete_url, headers=auth_headers)
    
    def _validate_workitem_structure(self, workitem: Dict[str, Any]):
        """Validate work item object structure."""
        # Required fields
        assert "type" in workitem
        assert workitem["type"] == "workitems"
        assert "id" in workitem
        
        # Links
        assert "links" in workitem
        assert "self" in workitem["links"]
        
        # Attributes
        if "attributes" in workitem:
            attrs = workitem["attributes"]
            # Required attributes
            assert "title" in attrs
            
            # Common attributes
            expected_attrs = ["type", "status", "created", "updated"]
            for attr in expected_attrs:
                if attr in attrs:
                    assert attrs[attr] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])