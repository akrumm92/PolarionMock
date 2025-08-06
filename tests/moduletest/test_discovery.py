"""
Discovery tests to explore available resources in Polarion.
These tests help identify valid IDs for other tests.
"""

import pytest
import os
from .test_helpers import save_response_to_json


class TestDiscovery:
    """Discovery tests to find available resources."""
    
    @pytest.mark.integration
    def test_discover_project_spaces(self, polarion_client, test_project_id):
        """Discover all spaces in a project using document-based discovery."""
        try:
            # Use the new document-based space discovery method
            result = polarion_client.get_all_project_documents_and_spaces(
                project_id=test_project_id,
                max_pages=5  # Limit for testing
            )
            
            spaces = result.get("spaces", [])
            documents = result.get("documents", [])
            meta = result.get("meta", {})
            
            discovery_data = {
                "project_id": test_project_id,
                "spaces": spaces,
                "document_count": len(documents),
                "meta": {
                    "total_spaces": len(spaces),
                    "total_documents": len(documents),
                    "pages_fetched": meta.get("pages_fetched", 0),
                    "note": "Spaces extracted from document IDs (projectId/spaceId/documentId pattern)"
                },
                "sample_documents": documents[:5] if documents else []  # First 5 documents as sample
            }
            
            save_response_to_json("discovery_project_spaces_and_documents", discovery_data)
            
            # Log the results
            print(f"\nDiscovered {len(spaces)} spaces: {spaces}")
            print(f"Found {len(documents)} documents across all spaces")
            
            if not spaces:
                pytest.skip("No spaces found in project (might be empty project)")
                
        except Exception as e:
            pytest.skip(f"Could not discover project spaces: {e}")
    
    @pytest.mark.integration
    def test_discover_documents_in_default_space(self, polarion_client, test_project_id):
        """Discover documents in the default space using the new method."""
        try:
            # Use the new list_documents_in_space method
            documents = polarion_client.list_documents_in_space(
                project_id=test_project_id,
                space_id="_default",
                page_size=100
            )
            
            # Extract document IDs and names
            doc_list = []
            for doc in documents.get("data", []):
                doc_info = {
                    "id": doc.get("id"),
                    "type": doc.get("type"),
                    "moduleName": doc.get("attributes", {}).get("moduleName"),
                    "title": doc.get("attributes", {}).get("title", ""),
                    "spaceId": doc.get("attributes", {}).get("spaceId", "_default")
                }
                doc_list.append(doc_info)
            
            discovery_data = {
                "project_id": test_project_id,
                "space_id": "_default",
                "documents": doc_list,
                "meta": documents.get("meta", {}),
                "total_documents": len(doc_list)
            }
            
            save_response_to_json("discovery_documents_in_space", discovery_data)
            
            if not doc_list:
                pytest.skip("No documents found in default space")
                
        except Exception as e:
            pytest.skip(f"Could not discover documents: {e}")
    
    @pytest.mark.integration
    def test_discover_work_item_types(self, polarion_client, test_project_id):
        """Discover available work item types in project."""
        try:
            # Get a sample of work items to see what types exist
            work_items = polarion_client.get_work_items(
                project_id=test_project_id,
                **{"page[size]": 50}
            )
            
            # Extract unique work item types
            types = set()
            for item in work_items.get("data", []):
                item_type = item.get("attributes", {}).get("type")
                if item_type:
                    types.add(item_type)
            
            discovery_data = {
                "project_id": test_project_id,
                "work_item_types": sorted(list(types)),
                "sample_ids": [],
                "meta": {
                    "total_items_checked": len(work_items.get("data", []))
                }
            }
            
            # Get sample IDs for each type
            for wi_type in sorted(types):
                for item in work_items.get("data", []):
                    if item.get("attributes", {}).get("type") == wi_type:
                        discovery_data["sample_ids"].append({
                            "type": wi_type,
                            "id": item["id"],
                            "title": item.get("attributes", {}).get("title", "")[:50]
                        })
                        break
            
            save_response_to_json("discovery_work_item_types", discovery_data)
            
        except Exception as e:
            pytest.skip(f"Could not discover work item types: {e}")
    
    @pytest.mark.integration
    def test_discover_all_projects(self, polarion_client):
        """Discover all accessible projects."""
        try:
            # Try to get all projects
            response = polarion_client._request("GET", "/projects")
            projects = response.json()
            
            # Extract project information
            discovery_data = {
                "projects": [],
                "meta": {
                    "total_projects": len(projects.get("data", []))
                }
            }
            
            for project in projects.get("data", []):
                proj_info = {
                    "id": project["id"],
                    "name": project.get("attributes", {}).get("name", ""),
                    "description": project.get("attributes", {}).get("description", "")[:100]
                }
                discovery_data["projects"].append(proj_info)
            
            save_response_to_json("discovery_all_projects", discovery_data)
            
        except Exception as e:
            # If can't list all projects, at least save the test project
            discovery_data = {
                "projects": [{
                    "id": test_project_id,
                    "note": "Could not list all projects, showing test project only"
                }],
                "error": str(e)
            }
            save_response_to_json("discovery_all_projects", discovery_data)
    
    @pytest.mark.integration 
    def test_discover_sample_documents(self, polarion_client, test_project_id):
        """Try to discover documents by common naming patterns."""
        common_doc_names = [
            "requirements",
            "specification", 
            "test",
            "design",
            "architecture",
            "manual",
            "guide",
            "readme"
        ]
        
        discovered_docs = []
        
        for doc_name in common_doc_names:
            for space in ["_default", "Default"]:
                doc_id = f"{test_project_id}/{space}/{doc_name}"
                try:
                    doc = polarion_client.get_document(doc_id)
                    discovered_docs.append({
                        "id": doc_id,
                        "title": doc["data"]["attributes"].get("title", ""),
                        "type": doc["data"]["attributes"].get("type", ""),
                        "status": "found"
                    })
                except:
                    # Document doesn't exist
                    pass
        
        discovery_data = {
            "project_id": test_project_id,
            "discovered_documents": discovered_docs,
            "patterns_tried": [f"{test_project_id}/_default/{name}" for name in common_doc_names],
            "meta": {
                "documents_found": len(discovered_docs),
                "patterns_checked": len(common_doc_names)
            }
        }
        
        save_response_to_json("discovery_sample_documents", discovery_data)
        
        if not discovered_docs:
            pytest.skip("No documents found with common naming patterns")
    
    @pytest.mark.integration
    def test_discover_all_documents_in_all_spaces(self, polarion_client, test_project_id):
        """Discover all documents across all spaces in a project."""
        try:
            # First get all spaces
            spaces = polarion_client.get_project_spaces(test_project_id)
            
            all_documents = {}
            total_doc_count = 0
            
            # For each space, get documents
            for space_id in spaces:
                try:
                    documents = polarion_client.list_documents_in_space(
                        project_id=test_project_id,
                        space_id=space_id,
                        page_size=200
                    )
                    
                    doc_ids = []
                    for doc in documents.get("data", []):
                        doc_ids.append({
                            "id": doc.get("id"),
                            "moduleName": doc.get("attributes", {}).get("moduleName", ""),
                            "title": doc.get("attributes", {}).get("title", "")[:100]  # Truncate long titles
                        })
                    
                    all_documents[space_id] = {
                        "document_count": len(doc_ids),
                        "documents": doc_ids
                    }
                    total_doc_count += len(doc_ids)
                    
                except Exception as e:
                    all_documents[space_id] = {
                        "error": str(e),
                        "document_count": 0,
                        "documents": []
                    }
            
            discovery_data = {
                "project_id": test_project_id,
                "spaces_checked": spaces,
                "total_spaces": len(spaces),
                "total_documents": total_doc_count,
                "documents_by_space": all_documents,
                "meta": {
                    "note": "Complete document discovery across all project spaces"
                }
            }
            
            save_response_to_json("discovery_all_documents_all_spaces", discovery_data)
            
            print(f"\nDiscovery Summary for {test_project_id}:")
            print(f"- Found {len(spaces)} space(s)")
            print(f"- Found {total_doc_count} document(s) total")
            for space, info in all_documents.items():
                print(f"  - Space '{space}': {info['document_count']} documents")
                
        except Exception as e:
            pytest.skip(f"Could not complete full document discovery: {e}")