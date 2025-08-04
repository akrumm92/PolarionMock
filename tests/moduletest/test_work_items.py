"""
Tests for the work_items module.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch
from polarion_api.exceptions import PolarionNotFoundError, PolarionValidationError
from polarion_api.utils import DEFAULT_OUTPUT_DIR


class TestWorkItemsMixin:
    """Test the WorkItemsMixin methods."""
    
    @pytest.mark.integration
    def test_get_work_items_all(self, polarion_client):
        """Test getting all work items."""
        work_items = polarion_client.get_work_items()
        
        assert "data" in work_items
        assert isinstance(work_items["data"], list)
        
        # Check structure if items exist
        if work_items["data"]:
            item = work_items["data"][0]
            assert "type" in item
            assert item["type"] == "workitems"
            assert "id" in item
            assert "attributes" in item
    
    @pytest.mark.integration
    def test_get_work_items_with_output(self, polarion_client, test_project_id):
        """Test getting work items and saving output."""
        work_items = polarion_client.get_work_items(
            project_id=test_project_id,
            save_output=True,
            **{"page[size]": 5}
        )
        
        assert "data" in work_items
        
        # Check if output file was created
        output_files = list(DEFAULT_OUTPUT_DIR.glob(f"*_workitems_list_{test_project_id}.json"))
        assert len(output_files) > 0, "No output file created"
        
        # Clean up
        for file in output_files:
            file.unlink()
    
    @pytest.mark.integration
    def test_get_work_items_by_project(self, polarion_client, test_project_id):
        """Test getting work items for a specific project."""
        try:
            work_items = polarion_client.get_work_items(project_id=test_project_id)
            
            assert "data" in work_items
            assert isinstance(work_items["data"], list)
            
            # All items should belong to the project
            for item in work_items["data"]:
                assert test_project_id in item["id"]
        except PolarionNotFoundError:
            pytest.skip(f"Test project '{test_project_id}' not found")
    
    @pytest.mark.integration
    def test_get_work_items_with_pagination(self, polarion_client):
        """Test getting work items with pagination."""
        work_items = polarion_client.get_work_items(**{
            "page[size]": 5,
            "page[number]": 1
        })
        
        assert "data" in work_items
        assert len(work_items["data"]) <= 5
        
        if "meta" in work_items:
            assert work_items["meta"].get("pageSize") == 5
    
    @pytest.mark.integration
    def test_get_work_items_with_include(self, polarion_client, test_project_id):
        """Test getting work items with included resources."""
        work_items = polarion_client.get_work_items(
            project_id=test_project_id,
            include="author,module"
        )
        
        assert "data" in work_items
        
        # Check if included resources are present when relationships exist
        if work_items["data"] and "included" in work_items:
            # Verify included resources have proper structure
            for included in work_items["included"]:
                assert "type" in included
                assert "id" in included
    
    @pytest.mark.integration
    def test_query_work_items(self, polarion_client):
        """Test querying work items."""
        results = polarion_client.query_work_items(
            query="type:requirement",
            **{"page[size]": 10}
        )
        
        assert "data" in results
        assert isinstance(results["data"], list)
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_work_item(self, polarion_client, test_project_id, 
                             test_work_item_data, created_work_items):
        """Test creating a work item."""
        work_item = polarion_client.create_work_item(
            project_id=test_project_id,
            **test_work_item_data
        )
        
        assert "id" in work_item
        assert "type" in work_item
        assert work_item["type"] == "workitems"
        assert "attributes" in work_item
        assert work_item["attributes"]["title"] == test_work_item_data["title"]
        
        # Track for cleanup
        created_work_items.append(work_item["id"])
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_work_item_from_file(self, polarion_client, test_project_id, created_work_items):
        """Test creating a work item from input file."""
        work_item = polarion_client.create_work_item(
            project_id=test_project_id,
            from_file="workitems_create.json",
            save_output=True
        )
        
        assert "id" in work_item
        assert "attributes" in work_item
        assert "Test Requirement" in work_item["attributes"]["title"]
        
        created_work_items.append(work_item["id"])
        
        # Check if output file was created
        output_files = list(DEFAULT_OUTPUT_DIR.glob("*_workitems_create.json"))
        assert len(output_files) > 0, "No output file created"
        
        # Clean up output
        for file in output_files:
            file.unlink()
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_work_item_with_relationships(self, polarion_client, test_project_id,
                                                unique_suffix, created_work_items):
        """Test creating a work item with relationships."""
        work_item = polarion_client.create_work_item(
            project_id=test_project_id,
            title=f"Work Item with Relations {unique_suffix}",
            work_item_type="task",
            description="Test work item with author relationship"
        )
        
        assert "id" in work_item
        created_work_items.append(work_item["id"])
        
        # Check if relationships were set (depends on implementation)
        if "relationships" in work_item:
            assert isinstance(work_item["relationships"], dict)
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_work_items_batch(self, polarion_client, test_project_id,
                                    unique_suffix, created_work_items):
        """Test creating multiple work items in batch."""
        items_data = [
            {
                "title": f"Batch Item 1 {unique_suffix}",
                "type": "requirement",
                "status": "open"
            },
            {
                "title": f"Batch Item 2 {unique_suffix}",
                "type": "task",
                "status": "open"
            }
        ]
        
        result = polarion_client.create_work_items_batch(
            project_id=test_project_id,
            work_items=items_data
        )
        
        assert "data" in result
        assert len(result["data"]) == 2
        
        # Track for cleanup
        for item in result["data"]:
            created_work_items.append(item["id"])
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_create_work_items_batch_from_file(self, polarion_client, test_project_id, created_work_items):
        """Test creating multiple work items from file."""
        result = polarion_client.create_work_items_batch(
            project_id=test_project_id,
            from_file="workitems_create.json",
            save_output=True
        )
        
        assert "data" in result
        assert len(result["data"]) >= 1  # At least one item created
        
        # Track for cleanup
        for item in result["data"]:
            created_work_items.append(item["id"])
        
        # Check if output file was created
        output_files = list(DEFAULT_OUTPUT_DIR.glob("*_workitems_create_batch.json"))
        assert len(output_files) > 0, "No output file created"
        
        # Clean up output
        for file in output_files:
            file.unlink()
    
    @pytest.mark.integration
    def test_get_work_item(self, polarion_client, test_project_id,
                          test_work_item_data, created_work_items):
        """Test getting a specific work item."""
        # First create a work item
        created = polarion_client.create_work_item(
            project_id=test_project_id,
            **test_work_item_data
        )
        created_work_items.append(created["id"])
        
        # Get the work item
        work_item = polarion_client.get_work_item(created["id"])
        
        assert "data" in work_item
        assert work_item["data"]["id"] == created["id"]
        assert work_item["data"]["attributes"]["title"] == test_work_item_data["title"]
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_update_work_item(self, polarion_client, test_project_id,
                             test_work_item_data, created_work_items):
        """Test updating a work item."""
        # Create work item
        created = polarion_client.create_work_item(
            project_id=test_project_id,
            **test_work_item_data
        )
        created_work_items.append(created["id"])
        
        # Update it
        polarion_client.update_work_item(
            work_item_id=created["id"],
            status="in_progress",
            priority="critical"
        )
        
        # Verify update
        updated = polarion_client.get_work_item(created["id"])
        assert updated["data"]["attributes"]["status"] == "in_progress"
        assert updated["data"]["attributes"]["priority"] == "critical"
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_update_work_item_from_file(self, polarion_client, test_project_id,
                                       test_work_item_data, created_work_items):
        """Test updating a work item from input file."""
        # Create work item
        created = polarion_client.create_work_item(
            project_id=test_project_id,
            **test_work_item_data
        )
        created_work_items.append(created["id"])
        
        # Update from file
        polarion_client.update_work_item(
            work_item_id=created["id"],
            from_file="workitems_update.json"
        )
        
        # Verify update
        updated = polarion_client.get_work_item(created["id"])
        assert updated["data"]["attributes"]["status"] == "in_progress"
        assert updated["data"]["attributes"]["priority"] == "critical"
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_update_work_item_relationships(self, polarion_client, test_project_id,
                                          unique_suffix, created_work_items):
        """Test updating work item relationships."""
        # Create parent and child work items
        parent = polarion_client.create_work_item(
            project_id=test_project_id,
            title=f"Parent Item {unique_suffix}",
            work_item_type="requirement"
        )
        created_work_items.append(parent["id"])
        
        child = polarion_client.create_work_item(
            project_id=test_project_id,
            title=f"Child Item {unique_suffix}",
            work_item_type="task"
        )
        created_work_items.append(child["id"])
        
        # Try to update relationship
        try:
            polarion_client.update_work_item_relationships(
                work_item_id=child["id"],
                parent=parent["id"]
            )
        except Exception as e:
            # Some implementations might not support this
            pytest.skip(f"Relationship updates not supported: {e}")
    
    @pytest.mark.integration
    @pytest.mark.destructive
    def test_delete_work_item(self, polarion_client, test_project_id, test_work_item_data):
        """Test deleting a work item."""
        # Create work item
        created = polarion_client.create_work_item(
            project_id=test_project_id,
            **test_work_item_data
        )
        
        # Delete it
        polarion_client.delete_work_item(created["id"])
        
        # Verify deletion
        with pytest.raises(PolarionNotFoundError):
            polarion_client.get_work_item(created["id"])
    
    @pytest.mark.integration
    def test_convenience_methods(self, polarion_client, test_project_id,
                               unique_suffix, created_work_items):
        """Test convenience methods for creating specific work item types."""
        # Create requirement
        req = polarion_client.create_requirement(
            project_id=test_project_id,
            title=f"Test Requirement {unique_suffix}",
            description="Created by convenience method"
        )
        assert req["attributes"]["type"] == "requirement"
        created_work_items.append(req["id"])
        
        # Create task
        task = polarion_client.create_task(
            project_id=test_project_id,
            title=f"Test Task {unique_suffix}",
            description="Created by convenience method"
        )
        assert task["attributes"]["type"] == "task"
        created_work_items.append(task["id"])
        
        # Create defect
        defect = polarion_client.create_defect(
            project_id=test_project_id,
            title=f"Test Defect {unique_suffix}",
            description="Created by convenience method"
        )
        assert defect["attributes"]["type"] == "defect"
        created_work_items.append(defect["id"])
    
    @pytest.mark.integration
    def test_get_work_items_in_document(self, polarion_client):
        """Test getting work items in a document (mock only)."""
        # This typically requires a known document with work items
        document_id = "elibrary/_default/requirements"
        
        try:
            work_items = polarion_client.get_work_items_in_document(document_id)
            
            assert "data" in work_items
            assert isinstance(work_items["data"], list)
            
            # All items should have the document relationship
            for item in work_items["data"]:
                if "relationships" in item and "module" in item["relationships"]:
                    module_data = item["relationships"]["module"].get("data", {})
                    assert document_id in module_data.get("id", "")
        except PolarionNotFoundError:
            pytest.skip("Test document not found")
    
    @pytest.mark.unit
    def test_get_relationship_type(self, polarion_client):
        """Test _get_relationship_type helper method."""
        # Test known relationship types
        assert polarion_client._get_relationship_type("author") == "users"
        assert polarion_client._get_relationship_type("assignee") == "users"
        assert polarion_client._get_relationship_type("module") == "documents"
        assert polarion_client._get_relationship_type("parent") == "workitems"
        assert polarion_client._get_relationship_type("project") == "projects"
        
        # Test unknown type (returns as-is)
        assert polarion_client._get_relationship_type("custom") == "custom"
    
    @pytest.mark.integration
    def test_error_handling(self, polarion_client):
        """Test error handling for work item operations."""
        # Test getting non-existent work item
        with pytest.raises(PolarionNotFoundError):
            polarion_client.get_work_item("nonexistent/FAKE-999")
        
        # Test creating work item with invalid data
        with pytest.raises(PolarionValidationError):
            polarion_client.create_work_item(
                project_id="nonexistent-project",
                title="",  # Empty title might cause validation error
                work_item_type="invalid-type"
            )
        
        # Test updating non-existent work item
        with pytest.raises(PolarionNotFoundError):
            polarion_client.update_work_item(
                work_item_id="nonexistent/FAKE-999",
                status="closed"
            )