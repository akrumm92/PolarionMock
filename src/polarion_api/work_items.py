"""
Work Items API methods for Polarion client.
"""

from typing import Dict, Any, Optional, List, Union
import logging

from .utils import (
    build_query_params,
    extract_id_parts,
    format_json_api_request,
    parse_json_api_response,
    validate_resource_id,
    merge_params,
    save_api_response,
    load_from_input,
    prepare_test_data,
    load_test_data_batch
)
from .models import WorkItemCreate, WorkItemUpdate, TextContent

logger = logging.getLogger(__name__)


class WorkItemsMixin:
    """Mixin class providing work item related methods."""
    
    # List and search methods
    
    def get_work_items(self, project_id: Optional[str] = None, 
                      save_output: bool = False, **params) -> Dict[str, Any]:
        """Get work items.
        
        Args:
            project_id: Optional project ID. If not provided, gets all work items.
            save_output: Whether to save response to output directory
            **params: Query parameters:
                - page[size]: Number of items per page
                - page[number]: Page number
                - include: Include related resources (e.g., "module,author")
                - query: Query string (e.g., "type:requirement AND status:open")
                - sort: Sort fields (e.g., "created,-updated")
                - fields[workitems]: Sparse fieldsets
                
        Returns:
            Work items collection response
        """
        if project_id:
            endpoint = f"/projects/{project_id}/workitems"
        else:
            endpoint = "/all/workitems"
        
        query_string = build_query_params(params)
        response = self._request("GET", f"{endpoint}{query_string}")
        result = parse_json_api_response(response.json())
        
        # Save output if requested
        if save_output:
            operation = f"list_{project_id}" if project_id else "list_all"
            save_api_response(result, "workitems", operation)
        
        return result
    
    def get_work_item(self, work_item_id: str, save_output: bool = False, **params) -> Dict[str, Any]:
        """Get a specific work item.
        
        Args:
            work_item_id: Work item ID (format: "project/item" or just "item")
            save_output: Whether to save response to output directory
            **params: Query parameters (include, fields)
            
        Returns:
            Work item resource
        """
        # Extract project and item IDs
        parts = extract_id_parts(work_item_id)
        
        if "project_id" in parts and "item_id" in parts:
            endpoint = f"/projects/{parts['project_id']}/workitems/{parts['item_id']}"
        else:
            # Assume it's in the default project
            if hasattr(self.config, 'default_project_id') and self.config.default_project_id:
                endpoint = f"/projects/{self.config.default_project_id}/workitems/{work_item_id}"
            else:
                raise ValueError(f"Invalid work item ID format: {work_item_id}")
        
        query_string = build_query_params(params)
        response = self._request("GET", f"{endpoint}{query_string}")
        result = parse_json_api_response(response.json())
        
        # Save output if requested
        if save_output:
            save_api_response(result, "workitems", f"get_{work_item_id.replace('/', '_')}")
        
        return result
    
    def query_work_items(self, query: str, project_id: Optional[str] = None, **params) -> Dict[str, Any]:
        """Query work items using Polarion query language.
        
        Args:
            query: Query string (e.g., "type:requirement AND status:open")
            project_id: Optional project ID to limit search
            **params: Additional query parameters
            
        Returns:
            Work items matching the query
        """
        params["query"] = query
        return self.get_work_items(project_id=project_id, **params)
    
    # Create methods
    
    def create_work_item(self, project_id: str, title: str = None, work_item_type: str = None,
                        description: Optional[Union[str, Dict[str, str]]] = None,
                        from_file: Optional[str] = None,
                        save_output: bool = False,
                        **attributes) -> Dict[str, Any]:
        """Create a new work item.
        
        Args:
            project_id: Project ID
            title: Work item title (can be loaded from file)
            work_item_type: Type (e.g., "requirement", "task", "defect")
            description: Optional description (string or TextContent dict)
            from_file: Load work item data from input file
            save_output: Whether to save response to output directory
            **attributes: Additional attributes (status, priority, severity, etc.)
            
        Returns:
            Created work item resource
        """
        # Load from file if specified
        if from_file:
            file_data = load_from_input(from_file)
            
            # If it's a list, take the first item
            if isinstance(file_data, list) and file_data:
                file_data = file_data[0]
            
            # Prepare data with unique suffix
            prepared_data = prepare_test_data(file_data)
            
            # Extract attributes
            attrs = prepared_data.get("attributes", prepared_data)
            
            # Override with any provided arguments
            if title:
                attrs["title"] = title
            if work_item_type:
                attrs["type"] = work_item_type
        else:
            # Build attributes from arguments
            attrs = {
                "title": title,
                "type": work_item_type
            }
            
            # Handle description
            if description:
                if isinstance(description, str):
                    attrs["description"] = {
                        "type": "text/plain",
                        "value": description
                    }
                else:
                    attrs["description"] = description
        
        # Add other attributes
        attrs.update(attributes)
        
        # Format request
        request_data = format_json_api_request("workitems", attrs)
        
        # Send request
        endpoint = f"/projects/{project_id}/workitems"
        response = self._request("POST", endpoint, json=request_data)
        
        result = parse_json_api_response(response.json())
        
        # Extract the created work item
        if "data" in result and isinstance(result["data"], list) and result["data"]:
            created_item = result["data"][0]
        else:
            created_item = result
        
        # Save output if requested
        if save_output:
            save_api_response(created_item, "workitems", "create")
        
        return created_item
    
    def create_work_items_batch(self, project_id: str, 
                              work_items: Optional[List[Dict[str, Any]]] = None,
                              from_file: Optional[str] = None,
                              save_output: bool = False) -> Dict[str, Any]:
        """Create multiple work items in a single request.
        
        Args:
            project_id: Project ID
            work_items: List of work item data dictionaries
            from_file: Load work items from input file
            save_output: Whether to save response to output directory
            
        Returns:
            Created work items response
        """
        # Load from file if specified
        if from_file:
            work_items = load_from_input(from_file)
            if not isinstance(work_items, list):
                work_items = [work_items]
            
            # Prepare each item with unique suffix
            work_items = [prepare_test_data(item) for item in work_items]
        
        # Format each work item
        data = []
        for item in work_items:
            # Extract attributes and relationships
            if "attributes" in item:
                attrs = item["attributes"]
                rels = item.get("relationships")
            else:
                attrs = item.copy()
                rels = attrs.pop("relationships", None)
            
            wi_data = {
                "type": "workitems",
                "attributes": attrs
            }
            if rels:
                wi_data["relationships"] = rels
            data.append(wi_data)
        
        request_data = {"data": data}
        
        endpoint = f"/projects/{project_id}/workitems"
        response = self._request("POST", endpoint, json=request_data)
        result = parse_json_api_response(response.json())
        
        # Save output if requested
        if save_output:
            save_api_response(result, "workitems", "create_batch")
        
        return result
    
    # Update methods
    
    def update_work_item(self, work_item_id: str, 
                        from_file: Optional[str] = None,
                        **attributes) -> None:
        """Update a work item.
        
        Args:
            work_item_id: Work item ID (format: "project/item")
            from_file: Load update data from input file
            **attributes: Attributes to update
            
        Note:
            Updates return 204 No Content on success
        """
        # Extract IDs
        parts = extract_id_parts(work_item_id)
        
        if "project_id" not in parts or "item_id" not in parts:
            raise ValueError(f"Invalid work item ID format: {work_item_id}")
        
        # Load from file if specified
        if from_file:
            file_data = load_from_input(from_file)
            
            # If it's a list, take the first item
            if isinstance(file_data, list) and file_data:
                file_data = file_data[0]
            
            # Extract attributes
            update_attrs = file_data.get("attributes", file_data)
            
            # Don't prepare with suffix for updates
            # Merge with provided attributes
            update_attrs.update(attributes)
            attributes = update_attrs
        
        # Format update request
        update_data = {
            "data": {
                "type": "workitems",
                "id": work_item_id,
                "attributes": attributes
            }
        }
        
        endpoint = f"/projects/{parts['project_id']}/workitems/{parts['item_id']}"
        self._request("PATCH", endpoint, json=update_data)
        
        logger.info(f"Updated work item: {work_item_id}")
    
    def update_work_item_relationships(self, work_item_id: str, **relationships) -> None:
        """Update work item relationships.
        
        Args:
            work_item_id: Work item ID
            **relationships: Relationships to update (e.g., parent, module, assignee)
        """
        parts = extract_id_parts(work_item_id)
        
        if "project_id" not in parts or "item_id" not in parts:
            raise ValueError(f"Invalid work item ID format: {work_item_id}")
        
        # Format relationships
        formatted_rels = {}
        for rel_name, rel_data in relationships.items():
            if isinstance(rel_data, str):
                # Simple ID provided
                formatted_rels[rel_name] = {
                    "data": {
                        "type": self._get_relationship_type(rel_name),
                        "id": rel_data
                    }
                }
            else:
                formatted_rels[rel_name] = rel_data
        
        update_data = {
            "data": {
                "type": "workitems",
                "id": work_item_id,
                "relationships": formatted_rels
            }
        }
        
        endpoint = f"/projects/{parts['project_id']}/workitems/{parts['item_id']}"
        self._request("PATCH", endpoint, json=update_data)
    
    # Delete methods
    
    def delete_work_item(self, work_item_id: str) -> None:
        """Delete a work item.
        
        Args:
            work_item_id: Work item ID
        """
        parts = extract_id_parts(work_item_id)
        
        if "project_id" not in parts or "item_id" not in parts:
            raise ValueError(f"Invalid work item ID format: {work_item_id}")
        
        endpoint = f"/projects/{parts['project_id']}/workitems/{parts['item_id']}"
        self._request("DELETE", endpoint)
        
        logger.info(f"Deleted work item: {work_item_id}")
    
    # Utility methods
    
    def _get_relationship_type(self, relationship_name: str) -> str:
        """Get the resource type for a relationship name."""
        type_mapping = {
            "author": "users",
            "assignee": "users",
            "module": "documents",
            "parent": "workitems",
            "children": "workitems",
            "project": "projects",
            "linkedWorkItems": "linkedworkitems",
            "attachments": "attachments",
            "comments": "comments"
        }
        return type_mapping.get(relationship_name, relationship_name)
    
    # Convenience methods
    
    def create_requirement(self, project_id: str, title: str, **kwargs) -> Dict[str, Any]:
        """Create a requirement work item."""
        return self.create_work_item(project_id, title, "requirement", **kwargs)
    
    def create_task(self, project_id: str, title: str, **kwargs) -> Dict[str, Any]:
        """Create a task work item."""
        return self.create_work_item(project_id, title, "task", **kwargs)
    
    def create_defect(self, project_id: str, title: str, **kwargs) -> Dict[str, Any]:
        """Create a defect/bug work item."""
        return self.create_work_item(project_id, title, "defect", **kwargs)
    
    def get_work_items_in_document(self, document_id: str, **params) -> Dict[str, Any]:
        """Get work items in a specific document.
        
        Args:
            document_id: Document ID (format: "project/space/document")
            **params: Query parameters
            
        Returns:
            Work items in the document
        """
        endpoint = f"/documents/{document_id}/workitems"
        query_string = build_query_params(params)
        response = self._request("GET", f"{endpoint}{query_string}")
        return parse_json_api_response(response.json())