"""
Documents module for Polarion API - FIXED VERSION
Corrects the space discovery to use only existing Polarion endpoints
"""

import logging
from typing import List, Dict, Any, Optional
from .base import PolarionClient

logger = logging.getLogger(__name__)


class DocumentsMixin:
    """Mixin for document-related operations."""
    
    def get_project_spaces(self, project_id: str) -> List[str]:
        """Discover spaces by trying to access known document names in potential spaces.
        
        Since Polarion has NO bulk endpoints for documents or spaces, we must:
        1. Try common space names with common document names
        2. Check which combinations return 200 OK
        
        Args:
            project_id: The project ID
            
        Returns:
            List of discovered space IDs
        """
        found_spaces = set()
        logger.info(f"Starting space discovery for project: {project_id}")
        
        # Common space names in Polarion projects
        potential_spaces = [
            "_default",      # Most common default space
            "Default",       # Alternative capitalization
            "Requirements",  # Common for requirements
            "TestCases",     # Common for test cases
            "Documents",     # Generic documents
            "Specifications",# Technical specs
            "Design",        # Design documents
            "Tests",         # Test documentation
            "Implementation",# Implementation docs
            "Maintenance",   # Maintenance docs
            "System",        # System level docs
            "Component",     # Component docs
            "Architecture",  # Architecture docs
            "ProductLayer",  # Product layer (various formats)
            "Product_Layer",
            "Product Layer",
            "product_layer"
        ]
        
        # Common document names that might exist
        common_doc_names = [
            "_project",      # Project root document (often exists)
            "index",         # Index document
            "readme",        # README document
            "overview",      # Overview document
            "requirements",  # Requirements document
            "specifications",# Specifications document
            "test",          # Test document
            "main",          # Main document
            "home"           # Home document
        ]
        
        for space in potential_spaces:
            space_found = False
            
            for doc_name in common_doc_names:
                if space_found:
                    break
                    
                try:
                    # Try to get a specific document
                    # Format: projectId/spaceId/documentId
                    doc_id = f"{project_id}/{space}/{doc_name}"
                    
                    # Use the get_document method which already exists
                    doc = self.get_document(doc_id)
                    
                    # If we get here without exception, the document exists
                    found_spaces.add(space)
                    space_found = True
                    logger.info(f"✅ Found space '{space}' via document '{doc_name}'")
                    
                except Exception as e:
                    # Document doesn't exist or space doesn't exist
                    logger.debug(f"Space '{space}' with document '{doc_name}' not accessible: {e}")
                    continue
        
        # Always try the root project document
        try:
            # Many projects have a root _project document
            doc_id = f"{project_id}/_project"
            doc = self.get_document(doc_id)
            # If successful, there's likely a default space
            found_spaces.add("_default")
            logger.info("✅ Found root _project document, assuming _default space exists")
        except:
            pass
        
        logger.info(f"Discovery completed: Found {len(found_spaces)} spaces")
        if found_spaces:
            logger.info(f"Discovered spaces: {sorted(list(found_spaces))}")
        else:
            logger.warning(f"No spaces found for project {project_id}. Project might be empty.")
        
        return sorted(list(found_spaces))
    
    def get_all_project_documents_and_spaces(self, project_id: str, 
                                            page_size: int = 100,
                                            max_pages: Optional[int] = None) -> Dict[str, Any]:
        """Discover spaces and attempt to get document information.
        
        Since there's no bulk endpoint, this method:
        1. Discovers spaces using get_project_spaces()
        2. For each space, tries common document names
        3. Returns what it can find
        
        Args:
            project_id: The project ID
            page_size: Ignored (kept for compatibility)
            max_pages: Ignored (kept for compatibility)
            
        Returns:
            Dictionary with discovered spaces and documents
        """
        logger.info(f"Starting document and space discovery for project: {project_id}")
        
        # First discover spaces
        spaces = self.get_project_spaces(project_id)
        
        # Try to get some documents from each space
        all_documents = []
        
        # Common document names to try
        doc_names_to_try = [
            "_project", "index", "readme", "overview",
            "requirements", "specifications", "test", "main"
        ]
        
        for space in spaces:
            logger.debug(f"Checking documents in space: {space}")
            
            for doc_name in doc_names_to_try:
                try:
                    doc_id = f"{project_id}/{space}/{doc_name}"
                    doc = self.get_document(doc_id)
                    
                    if doc and "data" in doc:
                        doc_info = {
                            "id": doc["data"].get("id", doc_id),
                            "space_id": space,
                            "document_name": doc_name,
                            "type": doc["data"].get("type", "documents"),
                            "attributes": doc["data"].get("attributes", {})
                        }
                        all_documents.append(doc_info)
                        logger.debug(f"Found document: {doc_id}")
                        
                except Exception as e:
                    logger.debug(f"Document {doc_id} not accessible: {e}")
                    continue
        
        result = {
            "spaces": spaces,
            "documents": all_documents,
            "meta": {
                "total_spaces": len(spaces),
                "total_documents": len(all_documents),
                "project_id": project_id,
                "note": "Limited discovery - Polarion has no bulk document endpoints"
            }
        }
        
        logger.info(f"Discovery completed: Found {len(spaces)} spaces and {len(all_documents)} documents")
        
        return result
    
    def list_documents_in_space(self, project_id: str, space_id: str, 
                               page_size: int = 100) -> Dict[str, Any]:
        """Try to list documents in a space.
        
        Since there's no bulk endpoint, this tries common document names.
        
        Args:
            project_id: The project ID
            space_id: The space ID
            page_size: Ignored (kept for compatibility)
            
        Returns:
            Dictionary with found documents
        """
        logger.info(f"Attempting to list documents in space: {project_id}/{space_id}")
        
        documents = []
        
        # Extended list of common document names
        doc_names_to_try = [
            "_project", "index", "readme", "overview", "home",
            "requirements", "specifications", "test", "main",
            "introduction", "getting-started", "guide", "manual",
            "architecture", "design", "implementation", "api",
            "changelog", "release-notes", "roadmap", "planning"
        ]
        
        for doc_name in doc_names_to_try:
            try:
                doc_id = f"{project_id}/{space_id}/{doc_name}"
                doc = self.get_document(doc_id)
                
                if doc and "data" in doc:
                    documents.append(doc["data"])
                    logger.debug(f"Found document: {doc_id}")
                    
            except Exception as e:
                logger.debug(f"Document {doc_name} not found in space {space_id}: {e}")
                continue
        
        result = {
            "data": documents,
            "meta": {
                "total": len(documents),
                "note": "Limited results - no bulk endpoint available"
            }
        }
        
        if documents:
            logger.info(f"Found {len(documents)} documents in space {space_id}")
        else:
            logger.warning(f"No documents found in space {space_id}")
        
        return result