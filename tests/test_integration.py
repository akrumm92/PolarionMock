"""
Integration tests that demonstrate complete workflows
Tests creating documents with work items
"""

import pytest
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TestIntegrationWorkflows:
    """Test complete workflows across multiple API endpoints."""
    
    @pytest.mark.mock_only
    @pytest.mark.integration
    def test_complete_document_workflow(self, api_base_url, auth_headers):
        """Test complete workflow: create document, add work items, query them."""
        
        # Step 1: Create a new document
        logger.info("Step 1: Creating new document")
        document_data = {
            "data": [{
                "type": "documents",
                "attributes": {
                    "moduleName": "test_workflow_doc",
                    "title": "Workflow Test Document",
                    "type": "req_specification",
                    "homePageContent": {
                        "type": "text/html",
                        "value": "<h1>Workflow Test</h1><p>This document contains work items</p>"
                    }
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/spaces/_default/documents"
        response = requests.post(url, headers=auth_headers, json=document_data)
        assert response.status_code == 201
        
        document_id = "myproject/_default/test_workflow_doc"
        
        # Step 2: Create work items in the document
        logger.info("Step 2: Creating work items in document")
        workitems_data = {
            "data": [
                {
                    "type": "workitems",
                    "attributes": {
                        "title": "Requirement 1: User Login",
                        "type": "requirement",
                        "priority": "high",
                        "description": {
                            "type": "text/plain",
                            "value": "Users must be able to login with email"
                        }
                    },
                    "relationships": {
                        "module": {
                            "data": {
                                "type": "documents",
                                "id": document_id
                            }
                        }
                    }
                },
                {
                    "type": "workitems",
                    "attributes": {
                        "title": "Requirement 2: Password Reset",
                        "type": "requirement",
                        "priority": "medium",
                        "description": {
                            "type": "text/plain",
                            "value": "Users must be able to reset their password"
                        }
                    },
                    "relationships": {
                        "module": {
                            "data": {
                                "type": "documents",
                                "id": document_id
                            }
                        }
                    }
                }
            ]
        }
        
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=workitems_data)
        assert response.status_code == 201
        
        created_workitems = response.json()["data"]
        assert len(created_workitems) == 2
        
        workitem_ids = [wi["id"] for wi in created_workitems]
        
        # Step 3: Query work items in the document
        logger.info("Step 3: Querying work items in document")
        url = f"{api_base_url}/projects/myproject/workitems?query=module.id:{document_id}"
        response = requests.get(url, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) >= 2  # At least our 2 work items
        
        # Step 4: Get document parts
        logger.info("Step 4: Getting document parts")
        url = f"{api_base_url}/projects/myproject/spaces/_default/documents/test_workflow_doc/parts?include=workItem"
        response = requests.get(url, headers=auth_headers)
        assert response.status_code == 200
        
        parts_data = response.json()
        assert len(parts_data["data"]) >= 2  # Should have parts for our work items
        
        # Verify included work items
        if "included" in parts_data:
            included_ids = [inc["id"] for inc in parts_data["included"]]
            for wi_id in workitem_ids:
                assert wi_id in included_ids
        
        # Step 5: Update a work item
        logger.info("Step 5: Updating work item status")
        wi_parts = workitem_ids[0].split("/")
        update_data = {
            "data": {
                "type": "workitems",
                "id": workitem_ids[0],
                "attributes": {
                    "status": "approved"
                }
            }
        }
        
        url = f"{api_base_url}/projects/{wi_parts[0]}/workitems/{wi_parts[1]}"
        response = requests.patch(url, headers=auth_headers, json=update_data)
        assert response.status_code == 200
        
        updated = response.json()["data"]
        assert updated["attributes"]["status"] == "approved"
        
        logger.info("Workflow test completed successfully!")
        
        # Cleanup
        logger.info("Cleaning up test data")
        # Delete work items
        for wi_id in workitem_ids:
            parts = wi_id.split("/")
            url = f"{api_base_url}/projects/{parts[0]}/workitems/{parts[1]}"
            requests.delete(url, headers=auth_headers)
        
        # Delete document
        url = f"{api_base_url}/projects/myproject/spaces/_default/documents/test_workflow_doc"
        requests.delete(url, headers=auth_headers)
    
    @pytest.mark.mock_only
    @pytest.mark.integration
    def test_workitem_move_between_documents(self, api_base_url, auth_headers):
        """Test moving work items between documents."""
        
        # Create two documents
        logger.info("Creating source and target documents")
        
        for doc_name, title in [("source_doc", "Source Document"), ("target_doc", "Target Document")]:
            doc_data = {
                "data": [{
                    "type": "documents",
                    "attributes": {
                        "moduleName": doc_name,
                        "title": title,
                        "type": "generic"
                    }
                }]
            }
            
            url = f"{api_base_url}/projects/myproject/spaces/_default/documents"
            response = requests.post(url, headers=auth_headers, json=doc_data)
            assert response.status_code == 201
        
        # Create work item in source document
        logger.info("Creating work item in source document")
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Mobile Work Item",
                    "type": "task"
                },
                "relationships": {
                    "module": {
                        "data": {
                            "type": "documents",
                            "id": "myproject/_default/source_doc"
                        }
                    }
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=workitem_data)
        assert response.status_code == 201
        
        workitem_id = response.json()["data"][0]["id"]
        wi_parts = workitem_id.split("/")
        
        # Move work item to target document
        logger.info("Moving work item to target document")
        move_data = {
            "targetDocument": "myproject/_default/target_doc"
        }
        
        url = f"{api_base_url}/projects/{wi_parts[0]}/workitems/{wi_parts[1]}/actions/moveToDocument"
        response = requests.post(url, headers=auth_headers, json=move_data)
        assert response.status_code == 200
        
        # Verify work item now belongs to target document
        url = f"{api_base_url}/projects/{wi_parts[0]}/workitems/{wi_parts[1]}"
        response = requests.get(url, headers=auth_headers)
        assert response.status_code == 200
        
        workitem = response.json()["data"]
        assert workitem["relationships"]["module"]["data"]["id"] == "myproject/_default/target_doc"
        
        logger.info("Work item successfully moved between documents!")
        
        # Cleanup
        logger.info("Cleaning up test data")
        # Delete work item
        url = f"{api_base_url}/projects/{wi_parts[0]}/workitems/{wi_parts[1]}"
        requests.delete(url, headers=auth_headers)
        
        # Delete documents
        for doc_name in ["source_doc", "target_doc"]:
            url = f"{api_base_url}/projects/myproject/spaces/_default/documents/{doc_name}"
            requests.delete(url, headers=auth_headers)


@pytest.mark.integration
class TestDataValidation:
    """Test data validation and error handling."""
    
    def test_invalid_project_returns_404(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test that invalid project returns proper error."""
        url = f"{api_base_url}/projects/non_existent_project/workitems"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["status"] == "404"
    
    @pytest.mark.mock_only
    def test_invalid_workitem_data(self, api_base_url, auth_headers):
        """Test creating work item with invalid data."""
        # Missing required title
        invalid_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "type": "requirement"
                    # Missing required 'title'
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=invalid_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "errors" in data
        assert "title" in data["errors"][0]["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])