"""
Simple example tests for common Polarion operations
Demonstrates creating work items, reading documents, and listing projects
"""

import pytest
import requests
import logging
import os
import json
from typing import List, Dict, Any
from tests.utils.test_helpers import APITestClient, log_test_data, assert_with_logging, log_test_section

logger = logging.getLogger(__name__)


class TestSimpleExamples:
    """Simple example tests for common operations."""
    
    @pytest.mark.integration
    def test_list_all_projects(self, api_base_url, auth_headers, test_env, log_test_info, capture_api_calls, http_session):
        """Simple test that lists all available projects."""
        log_test_info.info(f"Testing: List all projects in {test_env}")
        
        # Make request to list projects
        url = f"{api_base_url}/projects"
        log_test_info.debug(f"Request URL: {url}")
        
        response = http_session.get(url, headers=auth_headers)
        capture_api_calls(
            method="GET",
            url=url,
            status_code=response.status_code,
            response_data=response.json() if response.content else None
        )
        
        # Check response
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        log_test_info.info(f"✓ Response status: {response.status_code}")
        
        data = response.json()
        assert "data" in data, "Response must contain 'data' field"
        assert isinstance(data["data"], list), "Data must be a list"
        
        # Log found projects
        project_names = []
        for project in data["data"]:
            if "attributes" in project and "name" in project["attributes"]:
                project_names.append(project["attributes"]["name"])
        
        log_test_info.info(f"Found {len(data['data'])} projects: {', '.join(project_names)}")
        
        # Verify at least one project exists
        assert len(data["data"]) > 0, "At least one project should exist"
        
        # Verify project structure
        for project in data["data"]:
            assert project["type"] == "projects", "Type must be 'projects'"
            assert "id" in project, "Project must have an ID"
            assert "attributes" in project, "Project must have attributes"
            assert "links" in project, "Project must have links"
            
        return data["data"]
    
    @pytest.mark.mock_only
    @pytest.mark.integration
    def test_create_workitem_with_full_data(self, api_base_url, auth_headers, log_test_info, capture_api_calls, http_session):
        """Create a work item with all required fields from WorkItemRequest.json example."""
        log_test_info.info("Testing: Create work item with full data structure")
        
        # Get project ID from environment or use default
        project_id = os.getenv("TEST_PROJECT_ID", "myproject")
        log_test_info.debug(f"Using project ID: {project_id}")
        
        # Prepare work item data based on WorkItemRequest.json structure
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Test Work Item - Full Data",
                    "type": "requirement",
                    "description": {
                        "type": "text/html",
                        "value": "<p>This is a comprehensive test work item with all required fields</p>"
                    },
                    "status": "proposed",
                    "priority": "high",
                    "severity": "major",
                    "dueDate": "2025-12-31",
                    "initialEstimate": "5d",
                    "remainingEstimate": "3d",
                    "timeSpent": "2d",
                    "hyperlinks": [
                        {
                            "role": "ref_ext",
                            "uri": "https://example.com/reference"
                        }
                    ]
                },
                "relationships": {
                    "author": {
                        "data": {
                            "type": "users",
                            "id": "admin"
                        }
                    },
                    "assignee": {
                        "data": [
                            {
                                "type": "users",
                                "id": "john.doe"
                            }
                        ]
                    }
                }
            }]
        }
        
        # Create work item
        url = f"{api_base_url}/projects/{project_id}/workitems"
        log_test_info.debug(f"Creating work item at: {url}")
        log_test_info.debug(f"Work item request data: {json.dumps(workitem_data, indent=2)}")
        
        response = http_session.post(url, headers=auth_headers, json=workitem_data)
        capture_api_calls(
            method="POST",
            url=url,
            status_code=response.status_code,
            request_data=workitem_data,
            response_data=response.json() if response.content else None
        )
        
        # Verify creation
        assert response.status_code == 201, f"Expected status 201, got {response.status_code}: {response.text}"
        log_test_info.info(f"✓ Work item created successfully")
        
        data = response.json()
        assert "data" in data, "Response must contain 'data'"
        assert len(data["data"]) == 1, "Should create exactly one work item"
        
        created_item = data["data"][0]
        log_test_info.info(f"Created work item: {created_item['id']}")
        
        # Verify all attributes were set
        attrs = created_item["attributes"]
        assert attrs["title"] == "Test Work Item - Full Data"
        assert attrs["type"] == "requirement"
        assert attrs["status"] == "proposed"
        assert attrs["priority"] == "high"
        assert attrs["severity"] == "major"
        
        # Clean up - delete the created work item
        if created_item["id"]:
            parts = created_item["id"].split("/")
            delete_url = f"{api_base_url}/projects/{parts[0]}/workitems/{parts[1]}"
            log_test_info.debug(f"Cleaning up: DELETE {delete_url}")
            http_session.delete(delete_url, headers=auth_headers)
        
        return created_item
    
    @pytest.mark.integration
    def test_read_document_structure(self, api_base_url, auth_headers, test_env, log_test_info, capture_api_calls, http_session):
        """Read a specific document and its chapter structure."""
        log_test_info.info(f"Testing: Read document structure in {test_env}")
        
        # Use a known document ID based on environment
        if test_env == "mock":
            document_id = "elibrary/_default/requirements"
            project_id = "elibrary"
        else:
            # For production, we'd need to list documents first to get a valid ID
            # For now, skip if not mock
            pytest.skip("Document structure test currently only supported on mock")
        
        # First, get the document
        doc_url = f"{api_base_url}/documents/{document_id}"
        log_test_info.debug(f"Fetching document: {doc_url}")
        
        response = http_session.get(doc_url, headers=auth_headers)
        capture_api_calls(
            method="GET",
            url=doc_url,
            status_code=response.status_code,
            response_data=response.json() if response.content else None
        )
        
        if response.status_code == 404:
            pytest.skip(f"Document {document_id} not found")
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        log_test_info.info(f"✓ Document fetched successfully")
        
        doc_data = response.json()
        assert "data" in doc_data
        
        document = doc_data["data"]
        log_test_info.info(f"Document: {document['attributes']['title']}")
        
        # Now get the document parts (chapters/sections)
        parts_url = f"{api_base_url}/documents/{document_id}/parts"
        log_test_info.debug(f"Fetching document parts: {parts_url}")
        
        parts_response = http_session.get(parts_url, headers=auth_headers)
        capture_api_calls(
            method="GET",
            url=parts_url,
            status_code=parts_response.status_code,
            response_data=parts_response.json() if parts_response.content else None
        )
        
        # Document parts endpoint might not exist yet, so handle gracefully
        if parts_response.status_code == 404:
            log_test_info.warning("Document parts endpoint not implemented yet")
            
            # Try alternative: get work items in the document
            workitems_url = f"{api_base_url}/documents/{document_id}/workitems"
            wi_response = http_session.get(workitems_url, headers=auth_headers)
            
            if wi_response.status_code == 200:
                wi_data = wi_response.json()
                log_test_info.info(f"Document contains {len(wi_data.get('data', []))} work items")
                
                # Log work item titles
                for wi in wi_data.get("data", [])[:5]:  # First 5 items
                    if "attributes" in wi and "title" in wi["attributes"]:
                        log_test_info.debug(f"  - {wi['attributes']['title']}")
            else:
                log_test_info.info("No document structure information available")
        else:
            parts_data = parts_response.json()
            log_test_info.info(f"Document has {len(parts_data.get('data', []))} parts")
            
            # Log chapter structure
            for part in parts_data.get("data", []):
                if "attributes" in part:
                    log_test_info.debug(f"  - Part: {part['attributes'].get('type', 'unknown')}")
        
        return document


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])