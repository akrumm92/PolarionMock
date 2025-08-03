"""
Test script for Polarion Documents API
Tests run against both mock and production environments
"""

import pytest
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class TestDocuments:
    """Test suite for Documents API endpoints."""
    
    @pytest.mark.integration
    def test_list_all_documents(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test listing all documents."""
        url = f"{api_base_url}/all/documents"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Failed to list documents: {response.text}"
        
        # Validate JSON:API response structure
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Check meta information
        assert "meta" in data
        assert "totalCount" in data["meta"]
        
        # If documents exist, validate structure
        if len(data["data"]) > 0:
            document = data["data"][0]
            self._validate_document_structure(document)
        
        logger.info(f"[{test_env}] Found {len(data['data'])} documents")
    
    @pytest.mark.integration
    def test_list_space_documents(self, api_base_url, auth_headers, test_project_id, test_env, mock_server_running):
        """Test listing documents in a specific space."""
        url = f"{api_base_url}/projects/{test_project_id}/spaces/_default/documents"
        response = requests.get(url, headers=auth_headers)
        
        # Check if project exists
        if response.status_code == 404:
            pytest.skip(f"Project '{test_project_id}' not found in {test_env}")
        
        assert response.status_code == 200, f"Failed to list space documents: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        logger.info(f"[{test_env}] Found {len(data['data'])} documents in space _default")
    
    @pytest.mark.integration
    def test_get_document(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test getting a specific document."""
        # First, list documents to find one
        url = f"{api_base_url}/all/documents?page[size]=1"
        response = requests.get(url, headers=auth_headers)
        
        if response.status_code != 200 or len(response.json()["data"]) == 0:
            pytest.skip("No documents found to test")
        
        document_id = response.json()["data"][0]["id"]
        # Parse document ID to get components
        parts = document_id.split("/")
        if len(parts) != 3:
            pytest.skip(f"Invalid document ID format: {document_id}")
        
        project_id, space_id, doc_name = parts
        
        # Get specific document
        url = f"{api_base_url}/projects/{project_id}/spaces/{space_id}/documents/{doc_name}"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Failed to get document: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == document_id
        
        self._validate_document_structure(data["data"])
        
        logger.info(f"[{test_env}] Successfully retrieved document: {document_id}")
    
    @pytest.mark.mock_only
    def test_create_document(self, api_base_url, auth_headers):
        """Test creating a new document (mock only)."""
        document_data = {
            "data": [{
                "type": "documents",
                "attributes": {
                    "moduleName": "test_doc_001",
                    "title": "Test Document 001",
                    "type": "req_specification",
                    "homePageContent": {
                        "type": "text/html",
                        "value": "<h1>Test Document</h1><p>Created by automated test</p>"
                    }
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/spaces/_default/documents"
        response = requests.post(url, headers=auth_headers, json=document_data)
        
        assert response.status_code == 201, f"Failed to create document: {response.text}"
        
        data = response.json()
        assert data["data"][0]["attributes"]["title"] == "Test Document 001"
        
        logger.info("[mock] Successfully created test document")
        
        # Clean up - delete the document
        delete_url = f"{api_base_url}/projects/myproject/spaces/_default/documents/test_doc_001"
        requests.delete(delete_url, headers=auth_headers)
    
    @pytest.mark.integration
    def test_document_pagination(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test pagination for documents listing."""
        url = f"{api_base_url}/all/documents?page[size]=2&page[number]=1"
        response = requests.get(url, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination metadata
        assert "meta" in data
        meta = data["meta"]
        assert meta["pageSize"] == 2
        assert meta["currentPage"] == 1
        
        logger.info(f"[{test_env}] Document pagination working correctly")
    
    def _validate_document_structure(self, document: Dict[str, Any]):
        """Validate document object structure."""
        # Required fields
        assert "type" in document
        assert document["type"] == "documents"
        assert "id" in document
        
        # Links
        assert "links" in document
        assert "self" in document["links"]
        
        # Attributes
        if "attributes" in document:
            attrs = document["attributes"]
            # Common attributes
            expected_attrs = ["title", "name"]
            for attr in expected_attrs:
                if attr in attrs:
                    assert attrs[attr] is not None


class TestDocumentParts:
    """Test suite for Document Parts API endpoints."""
    
    @pytest.mark.integration  
    def test_list_document_parts(self, api_base_url, auth_headers, test_env, mock_server_running):
        """Test listing document parts."""
        if test_env == "mock":
            # Use known document from dummy data
            url = f"{api_base_url}/projects/elibrary/spaces/_default/documents/requirements/parts"
        else:
            pytest.skip("Document parts test requires known document structure")
        
        response = requests.get(url, headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip("Test document not found")
        
        assert response.status_code == 200, f"Failed to list document parts: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        logger.info(f"[{test_env}] Found {len(data['data'])} document parts")
    
    @pytest.mark.mock_only
    def test_add_workitem_to_document(self, api_base_url, auth_headers):
        """Test adding a work item to a document as a part."""
        # First create a work item
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Test Work Item for Document",
                    "type": "requirement",
                    "description": {
                        "type": "text/plain",
                        "value": "This work item will be added to a document"
                    }
                }
            }]
        }
        
        # Create work item
        url = f"{api_base_url}/projects/myproject/workitems"
        response = requests.post(url, headers=auth_headers, json=workitem_data)
        assert response.status_code == 201
        
        workitem_id = response.json()["data"][0]["id"]
        
        # Add work item to document as a part
        part_data = {
            "data": [{
                "type": "document_parts",
                "attributes": {
                    "type": "workitem"
                },
                "relationships": {
                    "workItem": {
                        "data": {
                            "type": "workitems",
                            "id": workitem_id
                        }
                    }
                }
            }]
        }
        
        url = f"{api_base_url}/projects/myproject/spaces/_default/documents/user_stories/parts"
        response = requests.post(url, headers=auth_headers, json=part_data)
        
        assert response.status_code == 201, f"Failed to add work item to document: {response.text}"
        
        logger.info(f"[mock] Successfully added work item {workitem_id} to document")
        
        # Clean up - delete the work item
        delete_url = f"{api_base_url}/projects/{workitem_id}"
        requests.delete(delete_url.replace("//", "/"), headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])