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
    
    def create_work_item_in_document(self, project_id: str, 
                                    space_id: str,
                                    document_name: str,
                                    title: str,
                                    work_item_type: str = "requirement",
                                    description: Optional[Union[str, Dict[str, str]]] = None,
                                    status: str = "draft",
                                    save_output: bool = False,
                                    previous_part_id: Optional[str] = None,
                                    **attributes) -> Dict[str, Any]:
        """Create a new work item and add it to a document (two-step process).
        
        This method implements the mandatory two-step process for creating WorkItems
        that are visible in Polarion documents:
        1. Create WorkItem with module relationship
        2. Add WorkItem to document content via Document Parts API
        
        Args:
            project_id: Project ID
            space_id: Space ID containing the document
            document_name: Document name
            title: Work item title
            work_item_type: Type (e.g., "requirement", "task", "defect")
            description: Optional description (string or TextContent dict)
            status: Work item status (default: "draft")
            save_output: Whether to save response to output directory
            previous_part_id: Optional ID of document part to insert after (e.g., "heading_PYTH-9397")
            **attributes: Additional attributes (priority, severity, etc.)
            
        Returns:
            Created work item resource with document integration status
        """
        from urllib.parse import quote
        
        # Step 1: Create WorkItem with module relationship
        logger.info(f"Step 1: Creating WorkItem with module relationship to {project_id}/{space_id}/{document_name}")
        
        # Build document ID
        document_id = f"{project_id}/{space_id}/{document_name}"
        
        # Build attributes
        attrs = {
            "title": title,
            "type": work_item_type,
            "status": status
        }
        
        # Handle description
        if description:
            if isinstance(description, str):
                attrs["description"] = {
                    "type": "text/html",
                    "value": f"<p>{description}</p>"
                }
            else:
                attrs["description"] = description
        
        # Add other attributes
        attrs.update(attributes)
        
        # Build relationships with module
        relationships = {
            "module": {
                "data": {
                    "type": "documents",
                    "id": document_id
                }
            }
        }
        
        # Format request
        request_data = {
            "data": [{
                "type": "workitems",
                "attributes": attrs,
                "relationships": relationships
            }]
        }
        
        # Send request
        endpoint = f"/projects/{project_id}/workitems"
        response = self._request("POST", endpoint, json=request_data)
        
        if response.status_code != 201:
            logger.error(f"Failed to create WorkItem: {response.status_code}")
            return {"error": f"Failed to create WorkItem: {response.status_code}"}
        
        result = parse_json_api_response(response.json())
        
        # Extract the created work item
        if "data" in result and isinstance(result["data"], list) and result["data"]:
            created_item = result["data"][0]
        else:
            created_item = result.get("data", result)
        
        work_item_id = created_item.get("id")
        logger.info(f"Created WorkItem: {work_item_id}")
        
        # Step 2: Add WorkItem to Document Content (CRITICAL!)
        logger.info(f"Step 2: Adding WorkItem to document content via Document Parts API")
        
        # URL encode space and document names
        space_encoded = quote(space_id, safe='')
        doc_encoded = quote(document_name, safe='')
        
        # Build document parts request
        parts_data = {
            "data": [{
                "type": "document_parts",
                "attributes": {
                    "type": "workitem"
                },
                "relationships": {
                    "workItem": {
                        "data": {
                            "type": "workitems",
                            "id": work_item_id
                        }
                    }
                }
            }]
        }
        
        # Add positioning if specified
        if previous_part_id:
            # Format the full document part ID (critical for Polarion API)
            full_part_id = f"{project_id}/{space_id}/{document_name}/{previous_part_id}"
            parts_data["data"][0]["relationships"]["previousPart"] = {
                "data": {
                    "type": "document_parts",
                    "id": full_part_id
                }
            }
            logger.info(f"Positioning WorkItem after part: {previous_part_id} (full ID: {full_part_id})")
        
        # Send request to Document Parts API
        parts_endpoint = f"projects/{project_id}/spaces/{space_encoded}/documents/{doc_encoded}/parts"
        parts_response = self._request("POST", parts_endpoint, json=parts_data)
        
        # Add integration status to result
        created_item["document_integration"] = {
            "step1_create": "success",
            "step2_add_to_document": "success" if parts_response.status_code == 201 else "failed",
            "document_id": document_id,
            "visible_in_document": parts_response.status_code == 201
        }
        
        if parts_response.status_code == 201:
            logger.info(f"✅ WorkItem {work_item_id} is now visible in the document!")
        else:
            logger.warning(f"⚠️ WorkItem created but not added to document: {parts_response.status_code}")
            created_item["document_integration"]["error"] = f"Document Parts API returned {parts_response.status_code}"
        
        # Save output if requested
        if save_output:
            save_api_response(created_item, "workitems", "create_in_document")
        
        return created_item
    
    def add_work_item_to_document(self, project_id: str,
                                 work_item_id: str,
                                 space_id: str,
                                 document_name: str,
                                 previous_part_id: Optional[str] = None) -> Dict[str, Any]:
        """Add an existing WorkItem to a document's content.
        
        This is Step 2 of the WorkItem-Document integration process.
        Without this step, WorkItems remain in the document's "Recycle Bin".
        
        Args:
            project_id: Project ID
            work_item_id: WorkItem ID (full format: "ProjectId/WORKITEM-ID")
            space_id: Space ID containing the document
            document_name: Document name
            previous_part_id: Optional ID of document part to insert after
            
        Returns:
            Operation result
        """
        from urllib.parse import quote
        
        logger.info(f"Adding WorkItem {work_item_id} to document {project_id}/{space_id}/{document_name}")
        
        # URL encode space and document names
        space_encoded = quote(space_id, safe='')
        doc_encoded = quote(document_name, safe='')
        
        # Build document parts request
        parts_data = {
            "data": [{
                "type": "document_parts",
                "attributes": {
                    "type": "workitem"
                },
                "relationships": {
                    "workItem": {
                        "data": {
                            "type": "workitems",
                            "id": work_item_id
                        }
                    }
                }
            }]
        }
        
        # Add positioning if specified
        if previous_part_id:
            # Format the full document part ID (critical for Polarion API)
            full_part_id = f"{project_id}/{space_id}/{document_name}/{previous_part_id}"
            parts_data["data"][0]["relationships"]["previousPart"] = {
                "data": {
                    "type": "document_parts",
                    "id": full_part_id
                }
            }
            logger.info(f"Positioning WorkItem after part: {previous_part_id} (full ID: {full_part_id})")
        
        # Send request to Document Parts API
        endpoint = f"projects/{project_id}/spaces/{space_encoded}/documents/{doc_encoded}/parts"
        response = self._request("POST", endpoint, json=parts_data)
        
        if response.status_code == 201:
            logger.info(f"✅ WorkItem {work_item_id} successfully added to document")
            return {
                "status": "success",
                "work_item_id": work_item_id,
                "document": f"{project_id}/{space_id}/{document_name}",
                "message": "WorkItem is now visible in the document"
            }
        else:
            logger.error(f"Failed to add WorkItem to document: {response.status_code}")
            return {
                "status": "error",
                "work_item_id": work_item_id,
                "document": f"{project_id}/{space_id}/{document_name}",
                "error": f"Document Parts API returned {response.status_code}",
                "response": response.text if response.text else None
            }
    
    def link_workitem_to_header(self, project_id: str,
                               child_workitem_id: str,
                               parent_header_id: str) -> Dict[str, Any]:
        """Create a parent-child relationship between a WorkItem and a header WorkItem.
        
        This links a WorkItem to appear under a specific header in the document structure.
        Note: This is separate from document positioning - the WorkItem must still be
        added to the document via add_work_item_to_document().
        
        Args:
            project_id: Project ID
            child_workitem_id: Child WorkItem ID (e.g., "PYTH-1234" or "Python/PYTH-1234")
            parent_header_id: Parent header WorkItem ID (e.g., "FCTS-9187" or "Python/FCTS-9187")
            
        Returns:
            Operation result
        """
        logger.info(f"Linking WorkItem {child_workitem_id} to header {parent_header_id}")
        
        # Extract short IDs if full format provided
        if "/" in child_workitem_id:
            child_short_id = child_workitem_id.split("/")[-1]
        else:
            child_short_id = child_workitem_id
            
        # Ensure parent_header_id is in full format
        if "/" not in parent_header_id:
            parent_header_id = f"{project_id}/{parent_header_id}"
        
        # Build linked work items request
        link_data = {
            "data": [{
                "type": "linkedworkitems",
                "attributes": {
                    "role": "parent"
                },
                "relationships": {
                    "workItem": {
                        "data": {
                            "type": "workitems",
                            "id": parent_header_id
                        }
                    }
                }
            }]
        }
        
        # Send request - use POST to linkedworkitems, NOT PATCH to relationships
        endpoint = f"projects/{project_id}/workitems/{child_short_id}/linkedworkitems"
        response = self._request("POST", endpoint, json=link_data)
        
        if response.status_code in [200, 201, 204]:
            logger.info(f"✅ Successfully linked {child_workitem_id} to parent {parent_header_id}")
            return {
                "status": "success",
                "child": child_workitem_id,
                "parent": parent_header_id,
                "message": "Parent-child relationship created"
            }
        elif response.status_code == 409:
            # Conflict - likely already linked
            logger.warning(f"Conflict when linking {child_workitem_id} to parent {parent_header_id}: {response.status_code}")
            return {
                "status": "error",
                "child": child_workitem_id,
                "parent": parent_header_id,
                "error": f"API returned {response.status_code} Conflict",
                "response": response.text if response.text else None,
                "conflict": True
            }
        else:
            logger.error(f"Failed to create parent-child link: {response.status_code}")
            return {
                "status": "error",
                "child": child_workitem_id,
                "parent": parent_header_id,
                "error": f"API returned {response.status_code}",
                "response": response.text if response.text else None
            }
    
    def update_work_item(self, work_item_id: str, attributes: Dict[str, Any] = None, 
                         relationships: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update a work item's attributes and/or relationships.
        
        Args:
            work_item_id: Work item ID (e.g., "PYTH-1234" or "Python/PYTH-1234")
            attributes: Dictionary of attributes to update (e.g., title, description, status, severity)
            relationships: Dictionary of relationships to update (e.g., parent, linkedWorkItems)
            
        Returns:
            Updated work item data
            
        Example:
            # Update attributes
            polarion_client.update_work_item(
                "PYTH-123",
                attributes={
                    "title": "Updated Title",
                    "description": {"type": "text/html", "value": "<p>New description</p>"},
                    "status": "Ready for Review",
                    "severity": "must_be"
                }
            )
            
            # Update relationships  
            polarion_client.update_work_item(
                "PYTH-123",
                relationships={
                    "parent": {
                        "data": {"type": "workitems", "id": "Python/PYTH-456"}
                    }
                }
            )
        """
        # Extract project and item IDs
        if "/" in work_item_id:
            project_id, item_id = work_item_id.split("/")
        else:
            # Assume it's for the current project if not specified
            item_id = work_item_id
            # Try to extract project from existing context or use a default
            project_id = getattr(self, '_default_project_id', 'Python')
            
        logger.info(f"Updating WorkItem {project_id}/{item_id}")
        
        # Build update payload
        update_data = {
            "data": {
                "type": "workitems",
                "id": f"{project_id}/{item_id}"
            }
        }
        
        if attributes:
            update_data["data"]["attributes"] = attributes
            logger.debug(f"Updating attributes: {attributes}")
            
        if relationships:
            # Format relationships properly
            formatted_rels = {}
            for rel_name, rel_data in relationships.items():
                if isinstance(rel_data, str):
                    # Simple ID provided - determine type based on relationship name
                    rel_type = self._get_relationship_type(rel_name)
                    formatted_rels[rel_name] = {
                        "data": {
                            "type": rel_type,
                            "id": rel_data
                        }
                    }
                else:
                    formatted_rels[rel_name] = rel_data
                    
            update_data["data"]["relationships"] = formatted_rels
            logger.debug(f"Updating relationships: {formatted_rels}")
        
        # Send PATCH request
        endpoint = f"projects/{project_id}/workitems/{item_id}"
        response = self._request("PATCH", endpoint, json=update_data)
        
        if response.status_code in [200, 202]:
            logger.info(f"✅ Successfully updated WorkItem {project_id}/{item_id}")
            result = response.json() if response.text else {}
            return {
                "status": "success",
                "id": f"{project_id}/{item_id}",
                "data": result.get("data", {})
            }
        else:
            logger.error(f"Failed to update WorkItem: {response.status_code}")
            return {
                "status": "error",
                "id": f"{project_id}/{item_id}",
                "error": f"API returned {response.status_code}",
                "response": response.text if response.text else None
            }

    def create_work_item_link(self, source_id: str, target_id: str, 
                             role: str = "relates_to", suspect: bool = False) -> Dict[str, Any]:
        """Create a link between two work items.
        
        Args:
            source_id: Source work item ID (e.g., "PYTH-123" or "Python/PYTH-123")
            target_id: Target work item ID (e.g., "PYTH-456" or "Python/PYTH-456")
            role: Link role (e.g., "relates_to", "depends_on", "blocks", "duplicates", "verifies")
            suspect: Whether the link is suspect (default: False)
            
        Returns:
            Operation result
            
        Common link roles:
            - relates_to: General relationship
            - depends_on: Source depends on target
            - blocks: Source blocks target
            - duplicates: Source duplicates target
            - verifies: Source verifies target (test case verifies requirement)
            - parent: Parent-child relationship (use link_workitem_to_header for headers)
        """
        # Extract IDs
        if "/" in source_id:
            source_project, source_item = source_id.split("/")
        else:
            source_project = getattr(self, '_default_project_id', 'Python')
            source_item = source_id
            
        if "/" not in target_id:
            target_id = f"{source_project}/{target_id}"
            
        logger.info(f"Creating link: {source_id} --[{role}]--> {target_id}")
        
        # Build link data
        link_data = {
            "data": [{
                "type": "linkedworkitems",
                "attributes": {
                    "role": role
                }
            }]
        }
        
        # Add optional suspect flag
        if suspect:
            link_data["data"][0]["attributes"]["suspect"] = suspect
            
        # Add target work item
        link_data["data"][0]["relationships"] = {
            "workItem": {
                "data": {
                    "type": "workitems",
                    "id": target_id
                }
            }
        }
        
        # Send request
        endpoint = f"projects/{source_project}/workitems/{source_item}/linkedworkitems"
        response = self._request("POST", endpoint, json=link_data)
        
        if response.status_code in [200, 201, 204]:
            logger.info(f"✅ Successfully created link: {source_id} --[{role}]--> {target_id}")
            return {
                "status": "success",
                "source": source_id,
                "target": target_id,
                "role": role,
                "message": f"Link created with role '{role}'"
            }
        elif response.status_code == 409:
            logger.warning(f"Link already exists: {source_id} --[{role}]--> {target_id}")
            return {
                "status": "error",
                "source": source_id,
                "target": target_id,
                "role": role,
                "error": "Link already exists (409 Conflict)",
                "response": response.text if response.text else None
            }
        else:
            logger.error(f"Failed to create link: {response.status_code}")
            return {
                "status": "error",
                "source": source_id,
                "target": target_id,
                "role": role,
                "error": f"API returned {response.status_code}",
                "response": response.text if response.text else None
            }
    
    def delete_work_item_link(self, source_id: str, target_id: str, role: str) -> Dict[str, Any]:
        """Delete a link between two work items.
        
        Args:
            source_id: Source work item ID
            target_id: Target work item ID  
            role: Link role to delete
            
        Returns:
            Operation result
        """
        # Extract IDs
        if "/" in source_id:
            source_project, source_item = source_id.split("/")
        else:
            source_project = getattr(self, '_default_project_id', 'Python')
            source_item = source_id
            
        if "/" not in target_id:
            target_id = f"{source_project}/{target_id}"
            
        logger.info(f"Deleting link: {source_id} --[{role}]-X-> {target_id}")
        
        # Build the link ID (format: source/role/target)
        link_id = f"{source_project}/{source_item}/{role}/{target_id}"
        
        # Send DELETE request
        endpoint = f"projects/{source_project}/workitems/{source_item}/linkedworkitems/{role}/{target_id}"
        response = self._request("DELETE", endpoint)
        
        if response.status_code in [200, 204]:
            logger.info(f"✅ Successfully deleted link: {source_id} --[{role}]-X-> {target_id}")
            return {
                "status": "success",
                "source": source_id,
                "target": target_id,
                "role": role,
                "message": f"Link with role '{role}' deleted"
            }
        elif response.status_code == 404:
            logger.warning(f"Link not found: {source_id} --[{role}]-- {target_id}")
            return {
                "status": "error",
                "source": source_id,
                "target": target_id,
                "role": role,
                "error": "Link not found (404)",
                "response": response.text if response.text else None
            }
        else:
            logger.error(f"Failed to delete link: {response.status_code}")
            return {
                "status": "error",
                "source": source_id,
                "target": target_id,
                "role": role,
                "error": f"API returned {response.status_code}",
                "response": response.text if response.text else None
            }

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