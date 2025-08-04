"""
Tests for the documents module.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch
from polarion_api.exceptions import PolarionNotFoundError, PolarionError
from polarion_api.utils import DEFAULT_OUTPUT_DIR


class TestDocumentsMixin:
    """Test the DocumentsMixin methods."""
    
    @pytest.mark.integration
    @pytest.mark.mock_only
    def test_get_document(self, polarion_client):
        """Test getting a specific document."""
        # Use known document from mock data
        document_id = "elibrary/_default/requirements"
        
        try:
            document = polarion_client.get_document(document_id)
            
            assert "data" in document
            assert document["data"]["id"] == document_id
            assert document["data"]["type"] == "documents"
            assert "attributes" in document["data"]
            
            # Check common attributes
            attrs = document["data"]["attributes"]
            assert "title" in attrs or "name" in attrs
        except PolarionNotFoundError:
            pytest.skip("Test document not found")
    
    @pytest.mark.integration
    @pytest.mark.mock_only
    def test_get_document_with_output(self, polarion_client):
        """Test getting document and saving output."""
        document_id = "elibrary/_default/requirements"
        
        try:
            document = polarion_client.get_document(
                document_id=document_id,
                save_output=True
            )
            
            assert "data" in document
            
            # Check if output file was created
            output_files = list(DEFAULT_OUTPUT_DIR.glob("*_documents_get_elibrary__default_requirements.json"))
            assert len(output_files) > 0, "No output file created"
            
            # Clean up
            for file in output_files:
                file.unlink()
        except PolarionNotFoundError:
            pytest.skip("Test document not found")
    
    @pytest.mark.integration
    def test_get_document_with_include(self, polarion_client):
        """Test getting document with included resources."""
        document_id = "elibrary/_default/requirements"
        
        try:
            document = polarion_client.get_document(
                document_id=document_id,
                include="author,project"
            )
            
            assert "data" in document
            
            # Check if includes are present when relationships exist
            if "relationships" in document["data"] and "included" in document:
                for included in document["included"]:
                    assert "type" in included
                    assert "id" in included
        except PolarionNotFoundError:
            pytest.skip("Test document not found")
    
    @pytest.mark.integration
    def test_get_documents_in_space(self, polarion_client, test_project_id):
        """Test getting documents in a space (may return 405)."""
        try:
            # This endpoint might not be supported
            documents = polarion_client.get_documents_in_space(
                project_id=test_project_id,
                space_id="_default"
            )
            
            assert "data" in documents
            assert isinstance(documents["data"], list)
        except PolarionError as e:
            # Expected - GET might not be allowed on this endpoint
            if e.status_code == 405:
                pytest.skip("GET not allowed on space documents endpoint")
            else:
                raise
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_document(self, polarion_client, test_project_id,
                           test_document_data, created_documents):
        """Test creating a document."""
        document = polarion_client.create_document(
            project_id=test_project_id,
            space_id="_default",
            **test_document_data
        )
        
        assert "id" in document
        assert "type" in document
        assert document["type"] == "documents"
        assert "attributes" in document
        assert document["attributes"]["title"] == test_document_data["title"]
        
        # Track for cleanup
        created_documents.append(document["id"])
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_document_from_file(self, polarion_client, test_project_id, created_documents):
        """Test creating a document from input file."""
        document = polarion_client.create_document(
            project_id=test_project_id,
            from_file="documents_create.json",
            save_output=True
        )
        
        assert "id" in document
        assert "attributes" in document
        assert "System Requirements Specification" in document["attributes"]["title"]
        
        created_documents.append(document["id"])
        
        # Check if output file was created
        output_files = list(DEFAULT_OUTPUT_DIR.glob("*_documents_create.json"))
        assert len(output_files) > 0, "No output file created"
        
        # Clean up output
        for file in output_files:
            file.unlink()
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_document_with_content(self, polarion_client, test_project_id,
                                        unique_suffix, created_documents):
        """Test creating a document with HTML content."""
        document = polarion_client.create_document(
            project_id=test_project_id,
            space_id="_default",
            module_name=f"test_spec_{unique_suffix}",
            title=f"Test Specification {unique_suffix}",
            document_type="test_specification",
            home_page_content=f"<h1>Test Spec</h1><p>Created at {unique_suffix}</p>"
        )
        
        assert document["attributes"]["type"] == "test_specification"
        assert "homePageContent" in document["attributes"]
        
        created_documents.append(document["id"])
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_update_document(self, polarion_client, test_project_id,
                           test_document_data, created_documents):
        """Test updating a document."""
        # Create document
        created = polarion_client.create_document(
            project_id=test_project_id,
            space_id="_default",
            **test_document_data
        )
        created_documents.append(created["id"])
        
        # Update it
        polarion_client.update_document(
            document_id=created["id"],
            title="Updated Document Title",
            status="approved"
        )
        
        # Verify update
        updated = polarion_client.get_document(created["id"])
        assert updated["data"]["attributes"]["title"] == "Updated Document Title"
        if "status" in updated["data"]["attributes"]:
            assert updated["data"]["attributes"]["status"] == "approved"
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_update_document_from_file(self, polarion_client, test_project_id,
                                     test_document_data, created_documents):
        """Test updating a document from input file."""
        # Create document
        created = polarion_client.create_document(
            project_id=test_project_id,
            space_id="_default",
            **test_document_data
        )
        created_documents.append(created["id"])
        
        # Update from file
        polarion_client.update_document(
            document_id=created["id"],
            from_file="documents_update.json"
        )
        
        # Verify update
        updated = polarion_client.get_document(created["id"])
        assert updated["data"]["attributes"]["title"] == "Updated Document Title"
        assert updated["data"]["attributes"]["status"] == "approved"
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_delete_document(self, polarion_client, test_project_id, test_document_data):
        """Test deleting a document."""
        # Create document
        created = polarion_client.create_document(
            project_id=test_project_id,
            space_id="_default",
            **test_document_data
        )
        
        # Delete it
        polarion_client.delete_document(created["id"])
        
        # Verify deletion
        with pytest.raises(PolarionNotFoundError):
            polarion_client.get_document(created["id"])
    
    @pytest.mark.integration
    @pytest.mark.mock_only
    def test_get_document_parts(self, polarion_client):
        """Test getting document parts."""
        document_id = "elibrary/_default/requirements"
        
        try:
            parts = polarion_client.get_document_parts(document_id)
            
            assert "data" in parts
            assert isinstance(parts["data"], list)
            
            # Check part structure if any exist
            if parts["data"]:
                part = parts["data"][0]
                assert "type" in part
                assert "attributes" in part
        except PolarionNotFoundError:
            pytest.skip("Test document not found")
        except PolarionError as e:
            if e.status_code == 404:
                pytest.skip("Document parts endpoint not implemented")
            raise
    
    @pytest.mark.integration
    @pytest.mark.mock_only
    def test_get_document_parts_with_output(self, polarion_client):
        """Test getting document parts and saving output."""
        document_id = "elibrary/_default/requirements"
        
        try:
            parts = polarion_client.get_document_parts(
                document_id=document_id,
                save_output=True
            )
            
            assert "data" in parts
            
            # Check if output file was created
            output_files = list(DEFAULT_OUTPUT_DIR.glob("*_documents_parts_elibrary__default_requirements.json"))
            assert len(output_files) > 0, "No output file created"
            
            # Clean up
            for file in output_files:
                file.unlink()
        except (PolarionNotFoundError, PolarionError):
            pytest.skip("Document parts not available")
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_add_work_item_to_document(self, polarion_client, test_project_id,
                                     test_work_item_data, test_document_data,
                                     created_work_items, created_documents):
        """Test adding a work item to a document."""
        # Create document
        document = polarion_client.create_document(
            project_id=test_project_id,
            space_id="_default",
            **test_document_data
        )
        created_documents.append(document["id"])
        
        # Create work item
        work_item = polarion_client.create_work_item(
            project_id=test_project_id,
            **test_work_item_data
        )
        created_work_items.append(work_item["id"])
        
        # Add work item to document
        try:
            result = polarion_client.add_work_item_to_document(
                document_id=document["id"],
                work_item_id=work_item["id"]
            )
            
            assert "data" in result or "id" in result
        except PolarionError as e:
            pytest.skip(f"Adding work items to documents not supported: {e}")
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_document_part(self, polarion_client, test_project_id,
                                test_document_data, unique_suffix, created_documents):
        """Test creating a document part."""
        # Create document
        document = polarion_client.create_document(
            project_id=test_project_id,
            space_id="_default",
            **test_document_data
        )
        created_documents.append(document["id"])
        
        # Create document part
        try:
            part = polarion_client.create_document_part(
                document_id=document["id"],
                part_type="heading",
                content=f"<h2>Section {unique_suffix}</h2>",
                level=2
            )
            
            assert "data" in part or "id" in part
        except PolarionError as e:
            pytest.skip(f"Creating document parts not supported: {e}")
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_convenience_methods(self, polarion_client, test_project_id,
                               unique_suffix, created_documents):
        """Test convenience methods for creating specific document types."""
        # Create requirement specification
        req_spec = polarion_client.create_requirement_specification(
            project_id=test_project_id,
            space_id="_default",
            module_name=f"req_spec_{unique_suffix}",
            title=f"Requirements Specification {unique_suffix}"
        )
        assert req_spec["attributes"]["type"] == "req_specification"
        created_documents.append(req_spec["id"])
        
        # Create test specification
        test_spec = polarion_client.create_test_specification(
            project_id=test_project_id,
            space_id="_default",
            module_name=f"test_spec_{unique_suffix}",
            title=f"Test Specification {unique_suffix}"
        )
        assert test_spec["attributes"]["type"] == "test_specification"
        created_documents.append(test_spec["id"])
    
    @pytest.mark.unit
    def test_document_id_extraction(self, polarion_client):
        """Test document ID parsing."""
        # Test valid document ID format
        doc_id = "myproject/_default/mydoc"
        
        # The client should handle this format correctly
        with patch.object(polarion_client, '_request') as mock_request:
            mock_request.return_value.json.return_value = {"data": {"id": doc_id}}
            
            # Test with save_output=True to generate output file
            result = polarion_client.get_document(doc_id, save_output=True)
            
            # Check that the correct endpoint was called
            expected_endpoint = "/projects/myproject/spaces/_default/documents/mydoc"
            mock_request.assert_called_once()
            assert expected_endpoint in mock_request.call_args[0][1]
            
            # Verify the response
            assert result == {"data": {"id": doc_id}}
    
    @pytest.mark.integration
    def test_error_handling(self, polarion_client):
        """Test error handling for document operations."""
        # Test getting non-existent document
        with pytest.raises(PolarionNotFoundError):
            polarion_client.get_document("nonexistent/_default/FAKE-DOC")
        
        # Test creating document with invalid data
        with pytest.raises(PolarionError):
            polarion_client.create_document(
                project_id="nonexistent-project",
                space_id="_default",
                module_name="",  # Empty module name might cause error
                title="Test",
                document_type="invalid-type"
            )
        
        # Test updating non-existent document
        with pytest.raises(PolarionNotFoundError):
            polarion_client.update_document(
                document_id="nonexistent/_default/FAKE-DOC",
                title="Updated"
            )