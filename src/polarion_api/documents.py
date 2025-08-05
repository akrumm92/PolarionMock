"""
Documents API methods for Polarion client.
"""

from typing import Dict, Any, Optional, List, Union
import logging

from .utils import (
    build_query_params,
    extract_id_parts,
    format_json_api_request,
    parse_json_api_response,
    validate_resource_id,
    save_api_response,
    load_from_input,
    prepare_test_data,
    load_test_data_batch
)
from .models import DocumentCreate, TextContent

logger = logging.getLogger(__name__)


class DocumentsMixin:
    """Mixin class providing document related methods."""
    
    # Get methods
    
    def get_document(self, document_id: str, save_output: bool = False, **params) -> Dict[str, Any]:
        """Get a specific document.
        
        Args:
            document_id: Document ID (format: "project/space/document")
            save_output: Whether to save response to output directory
            **params: Query parameters (include, fields)
            
        Returns:
            Document resource
        """
        # Extract parts
        parts = extract_id_parts(document_id)
        
        if "project_id" in parts and "space_id" in parts and "document_id" in parts:
            endpoint = f"/projects/{parts['project_id']}/spaces/{parts['space_id']}/documents/{parts['document_id']}"
        else:
            # Try direct endpoint
            endpoint = f"/documents/{document_id}"
        
        query_string = build_query_params(params)
        response = self._request("GET", f"{endpoint}{query_string}")
        result = parse_json_api_response(response.json())
        
        # Save output if requested
        if save_output:
            save_api_response(result, "documents", f"get_{document_id.replace('/', '_')}")
        
        return result
    
    def get_documents_in_space(self, project_id: str, space_id: str = "_default", 
                              **params) -> Dict[str, Any]:
        """Get documents in a specific space.
        
        Note: According to API spec, GET is not allowed on this endpoint.
        This method is included for completeness but may return 405.
        
        Args:
            project_id: Project ID
            space_id: Space ID (default: "_default")
            **params: Query parameters
            
        Returns:
            Documents collection or error
        """
        endpoint = f"/projects/{project_id}/spaces/{space_id}/documents"
        query_string = build_query_params(params)
        
        try:
            response = self._request("GET", f"{endpoint}{query_string}")
            return parse_json_api_response(response.json())
        except Exception as e:
            logger.warning(f"GET documents in space may not be supported: {str(e)}")
            raise
    
    # Create methods
    
    def create_document(self, project_id: str, space_id: str = "_default", 
                       module_name: str = None,
                       title: str = None, document_type: str = "req_specification",
                       home_page_content: Optional[Union[str, Dict[str, str]]] = None,
                       from_file: Optional[str] = None,
                       save_output: bool = False,
                       **attributes) -> Dict[str, Any]:
        """Create a new document.
        
        Args:
            project_id: Project ID
            space_id: Space ID (usually "_default")
            module_name: Module name (becomes part of document ID)
            title: Document title
            document_type: Document type (default: "req_specification")
            home_page_content: Optional home page content (string or TextContent dict)
            from_file: Load document data from input file
            save_output: Whether to save response to output directory
            **attributes: Additional attributes
            
        Returns:
            Created document resource
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
            if module_name:
                attrs["moduleName"] = module_name
            if title:
                attrs["title"] = title
            if document_type != "req_specification":
                attrs["type"] = document_type
        else:
            # Build attributes from arguments
            attrs = {
                "moduleName": module_name,
                "title": title,
                "type": document_type
            }
            
            # Handle home page content
        if home_page_content:
            if isinstance(home_page_content, str):
                attrs["homePageContent"] = {
                    "type": "text/html",
                    "value": home_page_content
                }
            else:
                attrs["homePageContent"] = home_page_content
        
        # Add other attributes
        attrs.update(attributes)
        
        # Format request
        request_data = format_json_api_request("documents", attrs)
        
        # Send request
        endpoint = f"/projects/{project_id}/spaces/{space_id}/documents"
        response = self._request("POST", endpoint, json=request_data)
        
        result = parse_json_api_response(response.json())
        
        # Extract the created document
        if "data" in result and isinstance(result["data"], list) and result["data"]:
            created_doc = result["data"][0]
        else:
            created_doc = result
        
        # Save output if requested
        if save_output:
            save_api_response(created_doc, "documents", "create")
        
        return created_doc
    
    # Update methods
    
    def update_document(self, document_id: str, 
                       from_file: Optional[str] = None,
                       **attributes) -> None:
        """Update a document.
        
        Args:
            document_id: Document ID (format: "project/space/document")
            from_file: Load update data from input file
            **attributes: Attributes to update
            
        Note:
            Updates return 204 No Content on success
        """
        # Extract IDs
        parts = extract_id_parts(document_id)
        
        if not all(k in parts for k in ["project_id", "space_id", "document_id"]):
            raise ValueError(f"Invalid document ID format: {document_id}")
        
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
                "type": "documents",
                "id": document_id,
                "attributes": attributes
            }
        }
        
        endpoint = f"/projects/{parts['project_id']}/spaces/{parts['space_id']}/documents/{parts['document_id']}"
        self._request("PATCH", endpoint, json=update_data)
        
        logger.info(f"Updated document: {document_id}")
    
    # Delete methods
    
    def delete_document(self, document_id: str) -> None:
        """Delete a document.
        
        Args:
            document_id: Document ID
        """
        parts = extract_id_parts(document_id)
        
        if not all(k in parts for k in ["project_id", "space_id", "document_id"]):
            raise ValueError(f"Invalid document ID format: {document_id}")
        
        endpoint = f"/projects/{parts['project_id']}/spaces/{parts['space_id']}/documents/{parts['document_id']}"
        self._request("DELETE", endpoint)
        
        logger.info(f"Deleted document: {document_id}")
    
    # Document parts methods
    
    def get_document_parts(self, document_id: str, save_output: bool = False, **params) -> Dict[str, Any]:
        """Get document parts (chapters, sections, work items).
        
        Args:
            document_id: Document ID
            save_output: Whether to save response to output directory
            **params: Query parameters
            
        Returns:
            Document parts collection
        """
        parts = extract_id_parts(document_id)
        
        if all(k in parts for k in ["project_id", "space_id", "document_id"]):
            endpoint = f"/projects/{parts['project_id']}/spaces/{parts['space_id']}/documents/{parts['document_id']}/parts"
        else:
            endpoint = f"/documents/{document_id}/parts"
        
        query_string = build_query_params(params)
        response = self._request("GET", f"{endpoint}{query_string}")
        result = parse_json_api_response(response.json())
        
        # Save output if requested
        if save_output:
            save_api_response(result, "documents", f"parts_{document_id.replace('/', '_')}")
        
        return result
    
    def add_work_item_to_document(self, document_id: str, work_item_id: str,
                                 part_type: str = "workitem") -> Dict[str, Any]:
        """Add a work item to a document as a part.
        
        Args:
            document_id: Document ID
            work_item_id: Work item ID to add
            part_type: Part type (default: "workitem")
            
        Returns:
            Created document part
        """
        parts = extract_id_parts(document_id)
        
        if not all(k in parts for k in ["project_id", "space_id", "document_id"]):
            raise ValueError(f"Invalid document ID format: {document_id}")
        
        # Format request
        part_data = {
            "data": [{
                "type": "document_parts",
                "attributes": {
                    "type": part_type
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
        
        endpoint = f"/projects/{parts['project_id']}/spaces/{parts['space_id']}/documents/{parts['document_id']}/parts"
        response = self._request("POST", endpoint, json=part_data)
        return parse_json_api_response(response.json())
    
    def create_document_part(self, document_id: str, part_type: str,
                           content: Optional[Union[str, Dict[str, str]]] = None,
                           **attributes) -> Dict[str, Any]:
        """Create a document part (chapter, text, etc.).
        
        Args:
            document_id: Document ID
            part_type: Part type (e.g., "heading", "text")
            content: Optional content (string or TextContent dict)
            **attributes: Additional attributes
            
        Returns:
            Created document part
        """
        parts = extract_id_parts(document_id)
        
        if not all(k in parts for k in ["project_id", "space_id", "document_id"]):
            raise ValueError(f"Invalid document ID format: {document_id}")
        
        # Build attributes
        attrs = {
            "type": part_type
        }
        
        # Handle content
        if content:
            if isinstance(content, str):
                attrs["content"] = {
                    "type": "text/html",
                    "value": content
                }
            else:
                attrs["content"] = content
        
        attrs.update(attributes)
        
        # Format request
        part_data = {
            "data": [{
                "type": "document_parts",
                "attributes": attrs
            }]
        }
        
        endpoint = f"/projects/{parts['project_id']}/spaces/{parts['space_id']}/documents/{parts['document_id']}/parts"
        response = self._request("POST", endpoint, json=part_data)
        return parse_json_api_response(response.json())
    
    # Convenience methods
    
    def create_requirement_specification(self, project_id: str, space_id: str,
                                       module_name: str, title: str, **kwargs) -> Dict[str, Any]:
        """Create a requirement specification document."""
        return self.create_document(
            project_id, space_id, module_name, title,
            document_type="req_specification", **kwargs
        )
    
    def create_test_specification(self, project_id: str, space_id: str,
                                 module_name: str, title: str, **kwargs) -> Dict[str, Any]:
        """Create a test specification document."""
        return self.create_document(
            project_id, space_id, module_name, title,
            document_type="test_specification", **kwargs
        )
    
    # Discovery methods
    
    def get_project_spaces(self, project_id: str) -> List[str]:
        """Get all spaces in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of space IDs
            
        Note:
            Most Polarion instances only have the default space "_default".
            This method attempts to discover spaces but may return only the default.
        """
        # There's no direct endpoint to list spaces in the REST API
        # We'll try common space names and see what exists
        common_spaces = ["_default", "Default", "default"]
        found_spaces = []
        
        for space in common_spaces:
            try:
                # Try to access the space by attempting to list documents
                endpoint = f"/projects/{project_id}/spaces/{space}/documents"
                # Use HEAD request to check if endpoint exists without getting data
                response = self._request("HEAD", endpoint)
                if response.status_code < 400:
                    found_spaces.append(space)
            except Exception:
                # Space doesn't exist or not accessible
                pass
        
        # If no spaces found, assume at least _default exists
        if not found_spaces:
            found_spaces = ["_default"]
            
        return found_spaces
    
    def list_documents_in_space(self, project_id: str, space_id: str = "_default",
                               fields: Optional[List[str]] = None,
                               include: Optional[str] = None,
                               page_size: int = 100,
                               page_number: int = 1) -> Dict[str, Any]:
        """List all documents in a project space.
        
        Args:
            project_id: Project ID
            space_id: Space ID (default: "_default")
            fields: List of fields to include
            include: Comma-separated list of related resources to include
            page_size: Number of results per page
            page_number: Page number to retrieve
            
        Returns:
            Dictionary containing:
            - data: List of document resources
            - meta: Metadata including total count
            - links: Pagination links
            
        Note:
            The GET endpoint might return 404 or 405. If so, this method
            will attempt alternative approaches to discover documents.
        """
        try:
            # First try the direct endpoint
            endpoint = f"/projects/{project_id}/spaces/{space_id}/documents"
            params = {
                "page[size]": page_size,
                "page[number]": page_number
            }
            
            if fields:
                params["fields[documents]"] = ",".join(fields)
            if include:
                params["include"] = include
                
            query_string = build_query_params(params)
            response = self._request("GET", f"{endpoint}{query_string}")
            return parse_json_api_response(response.json())
            
        except Exception as e:
            logger.warning(f"Direct document listing failed: {e}")
            
            # Alternative: Try POST with empty body (some APIs support this)
            try:
                endpoint = f"/projects/{project_id}/spaces/{space_id}/documents"
                response = self._request("POST", endpoint, json={"data": []})
                return parse_json_api_response(response.json())
            except:
                pass
            
            # Alternative: Use work items to discover documents
            try:
                from .work_items import WorkItemsMixin
                # Query work items and extract unique documents
                wi_response = self.query_work_items(
                    query=f"project.id:{project_id}",
                    page_size=1000
                )
                
                documents = set()
                for item in wi_response.get("data", []):
                    if "relationships" in item and "module" in item["relationships"]:
                        module_data = item["relationships"]["module"].get("data", {})
                        doc_id = module_data.get("id")
                        if doc_id and space_id in doc_id:
                            documents.add(doc_id)
                
                # Format as document list response
                doc_list = []
                for doc_id in sorted(documents):
                    parts = doc_id.split("/")
                    if len(parts) >= 3:
                        doc_list.append({
                            "type": "documents",
                            "id": doc_id,
                            "attributes": {
                                "moduleName": parts[-1],
                                "spaceId": parts[-2] if len(parts) > 2 else "_default"
                            }
                        })
                
                return {
                    "data": doc_list,
                    "meta": {
                        "totalCount": len(doc_list),
                        "note": "Documents discovered via work item relationships"
                    }
                }
                
            except Exception as e:
                logger.error(f"All document discovery methods failed: {e}")
                # Return empty result
                return {
                    "data": [],
                    "meta": {
                        "totalCount": 0,
                        "error": str(e)
                    }
                }