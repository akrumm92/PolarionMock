"""
Document and Space discovery via Work Items.
Since /projects/{projectId}/documents doesn't exist,
we use Work Items that have module relationships to discover documents.
"""

import logging
from typing import Dict, Any, Set, List, Optional
from .base import PolarionClient

logger = logging.getLogger(__name__)


class DocumentDiscoveryViaWorkItems:
    """Discover documents and spaces through Work Item module relationships."""
    
    def __init__(self, client):
        """Initialize with a Polarion client instance."""
        self.client = client
        
    def discover_all_documents_and_spaces(self, project_id: str, 
                                         max_pages: Optional[int] = None) -> Dict[str, Any]:
        """
        Discover all documents and spaces by querying work items with module relationships.
        
        Work Items in Polarion can be linked to documents via the 'module' relationship.
        By fetching all work items with their module relationships, we can:
        1. Identify all documents that contain work items
        2. Extract space IDs from document IDs (format: projectId/spaceId/documentId)
        
        Args:
            project_id: The project ID to discover
            max_pages: Maximum number of pages to fetch (None for all)
            
        Returns:
            Dictionary containing:
            - 'spaces': Set of unique space IDs
            - 'documents': Set of unique document IDs
            - 'work_items_count': Number of work items processed
            - 'meta': Additional metadata
        """
        logger.info(f"Starting document discovery via work items for project: {project_id}")
        
        discovered_documents = set()
        discovered_spaces = set()
        work_items_processed = 0
        page_number = 1
        pages_fetched = 0
        
        while True:
            try:
                # Query work items with module relationship included
                params = {
                    "page[size]": 100,  # Maximum per page
                    "page[number]": page_number,
                    "include": "module",  # Include module relationship
                    "fields[workitems]": "id",  # We only need IDs
                    "fields[documents]": "id,title,type"  # Module document fields
                }
                
                # Add query to only get work items that have a module
                # This reduces the amount of data we need to process
                params["query"] = "HAS_VALUE:module"
                
                logger.debug(f"Fetching work items page {page_number} with module relationships")
                
                response = self.client.get_work_items(
                    project_id=project_id,
                    **params
                )
                
                # Process work items
                work_items = response.get("data", [])
                included = response.get("included", [])
                
                if not work_items:
                    logger.debug("No more work items found")
                    break
                
                work_items_processed += len(work_items)
                
                # Extract module documents from relationships
                for work_item in work_items:
                    relationships = work_item.get("relationships", {})
                    module = relationships.get("module", {})
                    module_data = module.get("data")
                    
                    if module_data:
                        # Module data contains document reference
                        if isinstance(module_data, dict):
                            doc_id = module_data.get("id")
                            if doc_id:
                                discovered_documents.add(doc_id)
                                
                                # Extract space from document ID
                                # Format: projectId/spaceId/documentId
                                if "/" in doc_id:
                                    parts = doc_id.split("/")
                                    if len(parts) >= 3:
                                        space_id = parts[1]
                                        discovered_spaces.add(space_id)
                                        logger.debug(f"Found document '{doc_id}' in space '{space_id}'")
                
                # Also check included resources for document details
                for resource in included:
                    if resource.get("type") == "documents":
                        doc_id = resource.get("id")
                        if doc_id:
                            discovered_documents.add(doc_id)
                            
                            # Extract space from document ID
                            if "/" in doc_id:
                                parts = doc_id.split("/")
                                if len(parts) >= 3:
                                    space_id = parts[1]
                                    discovered_spaces.add(space_id)
                
                pages_fetched += 1
                
                # Check if there are more pages
                links = response.get("links", {})
                if not links.get("next"):
                    logger.debug("No more pages available")
                    break
                
                if max_pages and pages_fetched >= max_pages:
                    logger.info(f"Reached max pages limit ({max_pages})")
                    break
                
                page_number += 1
                
            except Exception as e:
                logger.error(f"Error fetching work items: {e}")
                break
        
        # Log results
        logger.info(f"Discovery completed:")
        logger.info(f"  - Work items processed: {work_items_processed}")
        logger.info(f"  - Documents found: {len(discovered_documents)}")
        logger.info(f"  - Spaces found: {len(discovered_spaces)}")
        
        if discovered_spaces:
            logger.info(f"  - Spaces: {sorted(discovered_spaces)}")
        
        return {
            "spaces": sorted(list(discovered_spaces)),
            "documents": sorted(list(discovered_documents)),
            "work_items_count": work_items_processed,
            "meta": {
                "pages_fetched": pages_fetched,
                "project_id": project_id,
                "discovery_method": "work_items_module_relationship",
                "note": "Only documents containing work items are discovered"
            }
        }
    
    def get_document_details(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get details for a list of document IDs.
        
        Since we can't list documents directly, but we can get individual documents,
        this method fetches details for each discovered document.
        
        Args:
            document_ids: List of document IDs to fetch
            
        Returns:
            List of document details
        """
        logger.info(f"Fetching details for {len(document_ids)} documents")
        
        document_details = []
        
        for doc_id in document_ids:
            try:
                # Get individual document
                doc = self.client.get_document(doc_id)
                
                if doc and "data" in doc:
                    doc_data = doc["data"]
                    
                    # Extract space from ID
                    space_id = None
                    if "/" in doc_id:
                        parts = doc_id.split("/")
                        if len(parts) >= 3:
                            space_id = parts[1]
                    
                    document_info = {
                        "id": doc_id,
                        "space_id": space_id,
                        "type": doc_data.get("type", "documents"),
                        "attributes": doc_data.get("attributes", {})
                    }
                    
                    document_details.append(document_info)
                    logger.debug(f"Retrieved document: {doc_id}")
                    
            except Exception as e:
                logger.warning(f"Could not fetch document {doc_id}: {e}")
                continue
        
        logger.info(f"Successfully retrieved {len(document_details)} documents")
        
        return document_details


def discover_via_workitems(client, project_id: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience function to discover documents and spaces via work items.
    
    Args:
        client: Polarion client instance
        project_id: Project ID to discover
        max_pages: Maximum pages to fetch
        
    Returns:
        Discovery results
    """
    discoverer = DocumentDiscoveryViaWorkItems(client)
    return discoverer.discover_all_documents_and_spaces(project_id, max_pages)