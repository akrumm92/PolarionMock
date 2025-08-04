"""
Test script for Polarion Documents API
Tests run against both mock and production environments
"""

import pytest
import requests
import logging
import os
from typing import List, Dict, Any
from tests.utils.test_helpers import APITestClient, log_test_data, assert_with_logging, log_test_section

logger = logging.getLogger(__name__)


class TestDocuments:
    """Test suite for Documents API endpoints."""
    
    @pytest.mark.integration
    def test_list_all_documents(self, api_base_url, auth_headers, test_env, mock_server_running, http_session):
        """Test listing all documents - endpoint should not exist."""
        url = f"{api_base_url}/all/documents"
        response = http_session.get(url, headers=auth_headers)
        
        # According to POLARION_API_SPECIFICATION.md, this endpoint doesn't exist
        assert response.status_code == 404, f"Expected 404 for non-existent endpoint, got {response.status_code}"
        
        # For a 404 error, we expect an error response
        data = response.json()
        assert "errors" in data
        
        logger.info(f"[{test_env}] Correctly received 404 for non-existent /all/documents endpoint")
    
    @pytest.mark.integration
    def test_list_space_documents(self, api_base_url, auth_headers, test_project_id, test_env, mock_server_running, http_session):
        """Test listing documents in a specific space."""
        url = f"{api_base_url}/projects/{test_project_id}/spaces/_default/documents"
        response = http_session.get(url, headers=auth_headers)
        
        # According to POLARION_API_SPECIFICATION.md, GET is not allowed on this endpoint
        assert response.status_code == 405, f"Expected 405 Method Not Allowed, got {response.status_code}"
        
        # For a 405 error, we expect an error response
        data = response.json()
        assert "errors" in data
        
        logger.info(f"[{test_env}] Correctly received 405 for GET on space documents endpoint")
    
    @pytest.mark.integration
    def test_get_document(self, api_base_url, auth_headers, test_env, mock_server_running, http_session):
        """Test getting a specific document."""
        # Since /all/documents doesn't exist, we need a known document ID
        if test_env == "mock":
            # Use a known document from mock data
            project_id = "elibrary"
            space_id = "_default"
            doc_name = "requirements"
            document_id = f"{project_id}/{space_id}/{doc_name}"
        else:
            pytest.skip("Production test requires known document ID")
        
        # Get specific document
        url = f"{api_base_url}/projects/{project_id}/spaces/{space_id}/documents/{doc_name}"
        response = http_session.get(url, headers=auth_headers)
        
        assert response.status_code == 200, f"Failed to get document: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == document_id
        
        self._validate_document_structure(data["data"])
        
        logger.info(f"[{test_env}] Successfully retrieved document: {document_id}")
    
    @pytest.mark.mock_only
    def test_create_document(self, api_base_url, auth_headers, http_session):
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
        response = http_session.post(url, headers=auth_headers, json=document_data)
        
        assert response.status_code == 201, f"Failed to create document: {response.text}"
        
        data = response.json()
        assert data["data"][0]["attributes"]["title"] == "Test Document 001"
        
        logger.info("[mock] Successfully created test document")
        
        # Clean up - delete the document
        delete_url = f"{api_base_url}/projects/myproject/spaces/_default/documents/test_doc_001"
        http_session.delete(delete_url, headers=auth_headers)
    
    @pytest.mark.production_only  # /all/documents doesn't exist
    def test_document_pagination(self, api_base_url, auth_headers, test_env, mock_server_running, http_session):
        """Test pagination for documents listing."""
        url = f"{api_base_url}/all/documents?page[size]=2&page[number]=1"
        response = http_session.get(url, headers=auth_headers)
        
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
    def test_list_document_parts(self, api_base_url, auth_headers, test_env, mock_server_running, http_session):
        """Test listing document parts."""
        if test_env == "mock":
            # Use known document from dummy data
            url = f"{api_base_url}/projects/elibrary/spaces/_default/documents/requirements/parts"
        else:
            pytest.skip("Document parts test requires known document structure")
        
        response = http_session.get(url, headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip("Test document not found")
        
        assert response.status_code == 200, f"Failed to list document parts: {response.text}"
        
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        logger.info(f"[{test_env}] Found {len(data['data'])} document parts")
    
    @pytest.mark.mock_only
    def test_add_workitem_to_document(self, api_base_url, auth_headers, test_project_id, http_session):
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
        url = f"{api_base_url}/projects/{test_project_id}/workitems"
        response = http_session.post(url, headers=auth_headers, json=workitem_data)
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
        response = http_session.post(url, headers=auth_headers, json=part_data)
        
        assert response.status_code == 201, f"Failed to add work item to document: {response.text}"
        
        logger.info(f"[mock] Successfully added work item {workitem_id} to document")
        
        # Clean up - delete the work item
        delete_url = f"{api_base_url}/projects/{workitem_id}"
        http_session.delete(delete_url.replace("//", "/"), headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])