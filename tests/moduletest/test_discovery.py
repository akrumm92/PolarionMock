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
        """Discover all spaces in a project."""
        try:
            # Try to get project info first
            project_endpoint = f"/projects/{test_project_id}"
            response = polarion_client._request("GET", project_endpoint)
            project_info = response.json()
            
            save_response_to_json("discovery_project_info", project_info)
            
            # Try to list spaces (this endpoint might not exist)
            spaces_endpoint = f"/projects/{test_project_id}/spaces"
            try:
                response = polarion_client._request("GET", spaces_endpoint)
                spaces = response.json()
                save_response_to_json("discovery_project_spaces", spaces)
            except Exception as e:
                # If spaces endpoint doesn't exist, try default space
                default_space = {
                    "data": [{
                        "type": "spaces",
                        "id": "_default",
                        "attributes": {
                            "name": "Default Space"
                        }
                    }],
                    "meta": {
                        "note": "Spaces endpoint not available, showing default space only"
                    }
                }
                save_response_to_json("discovery_project_spaces", default_space)
                
        except Exception as e:
            pytest.skip(f"Could not discover project info: {e}")
    
    @pytest.mark.integration
    def test_discover_documents_in_default_space(self, polarion_client, test_project_id):
        """Discover documents in the default space."""
        try:
            # Try different approaches to get documents
            
            # Approach 1: Direct documents endpoint
            try:
                endpoint = f"/projects/{test_project_id}/spaces/_default/documents"
                response = polarion_client._request("GET", endpoint)
                documents = response.json()
                save_response_to_json("discovery_documents_default_space", documents)
                return
            except Exception:
                pass
            
            # Approach 2: Try query endpoint
            try:
                # Use query to find documents
                query_params = {
                    "query": f"project.id:{test_project_id}",
                    "page[size]": 100
                }
                documents = polarion_client.query_work_items(**query_params)
                
                # Filter for documents (if work items include document references)
                discovery_data = {
                    "data": [],
                    "meta": {
                        "note": "Documents discovered via work item query",
                        "total_work_items": len(documents.get("data", []))
                    }
                }
                
                # Extract unique modules/documents from work items
                modules = set()
                for item in documents.get("data", []):
                    if "relationships" in item and "module" in item["relationships"]:
                        module_data = item["relationships"]["module"].get("data", {})
                        if module_data.get("id"):
                            modules.add(module_data["id"])
                
                discovery_data["data"] = [{"type": "documents", "id": doc_id} for doc_id in sorted(modules)]
                discovery_data["meta"]["unique_documents"] = len(modules)
                
                save_response_to_json("discovery_documents_via_workitems", discovery_data)
                
            except Exception as e:
                error_data = {
                    "error": str(e),
                    "suggestion": "Try using specific document IDs or check API permissions"
                }
                save_response_to_json("discovery_documents_error", error_data)
                
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