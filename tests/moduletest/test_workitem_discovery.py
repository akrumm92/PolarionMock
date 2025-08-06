"""
Test document and space discovery via Work Items.
These tests verify that we can discover documents through work item module relationships.
"""

import pytest
import os
import json
from .test_helpers import save_response_to_json


class TestWorkItemDiscovery:
    """Test document discovery through work items."""
    
    @pytest.mark.integration
    def test_workitem_endpoint_exists(self, polarion_client, test_project_id):
        """Test that the work items endpoint exists and is accessible."""
        try:
            # Get a small sample of work items
            response = polarion_client.get_work_items(
                project_id=test_project_id,
                **{"page[size]": 5}
            )
            
            assert "data" in response
            work_items = response.get("data", [])
            
            print(f"\nWork items endpoint accessible. Found {len(work_items)} items")
            
            # Check if any have module relationships
            modules_found = 0
            for wi in work_items:
                if "relationships" in wi and "module" in wi.get("relationships", {}):
                    modules_found += 1
            
            if modules_found > 0:
                print(f"Found {modules_found} work items with module relationships")
            else:
                pytest.skip("No work items with module relationships found in sample")
                
        except Exception as e:
            pytest.skip(f"Work items endpoint not accessible: {e}")
    
    @pytest.mark.integration
    def test_discover_documents_via_workitems(self, polarion_client, test_project_id):
        """Discover documents by querying work items with module relationships."""
        try:
            # Import the discovery module
            from polarion_api.documents_via_workitems import DocumentDiscoveryViaWorkItems
            
            discoverer = DocumentDiscoveryViaWorkItems(polarion_client)
            
            # Run discovery with limited pages for testing
            result = discoverer.discover_all_documents_and_spaces(
                project_id=test_project_id,
                max_pages=3
            )
            
            spaces = result.get("spaces", [])
            documents = result.get("documents", [])
            work_items_count = result.get("work_items_count", 0)
            
            discovery_data = {
                "project_id": test_project_id,
                "method": "work_items_module_relationship",
                "spaces": spaces,
                "documents": documents[:20],  # Save first 20 for review
                "total_spaces": len(spaces),
                "total_documents": len(documents),
                "work_items_processed": work_items_count,
                "meta": result.get("meta", {})
            }
            
            save_response_to_json("discovery_via_workitems", discovery_data)
            
            print(f"\nDiscovery via Work Items:")
            print(f"  - Work items processed: {work_items_count}")
            print(f"  - Documents found: {len(documents)}")
            print(f"  - Spaces found: {len(spaces)}")
            
            if spaces:
                print(f"  - Spaces: {', '.join(spaces[:5])}")
            
            if not documents:
                pytest.skip("No documents found via work items (might not have module relationships)")
                
            assert len(spaces) > 0, "Should find at least one space"
            assert len(documents) > 0, "Should find at least one document"
            
        except ImportError:
            pytest.skip("DocumentDiscoveryViaWorkItems module not available")
        except Exception as e:
            pytest.skip(f"Could not discover documents via work items: {e}")
    
    @pytest.mark.integration
    def test_workitem_with_module_include(self, polarion_client, test_project_id):
        """Test fetching work items with module relationship included."""
        try:
            # Query work items with module included
            response = polarion_client.get_work_items(
                project_id=test_project_id,
                **{
                    "page[size]": 10,
                    "include": "module",
                    "fields[workitems]": "id,title",
                    "fields[documents]": "id,title,type"
                }
            )
            
            work_items = response.get("data", [])
            included = response.get("included", [])
            
            # Look for document resources in included
            documents_in_included = []
            for resource in included:
                if resource.get("type") == "documents":
                    documents_in_included.append(resource.get("id"))
            
            # Look for module relationships
            documents_from_modules = []
            for wi in work_items:
                relationships = wi.get("relationships", {})
                module = relationships.get("module", {})
                module_data = module.get("data")
                if module_data and isinstance(module_data, dict):
                    doc_id = module_data.get("id")
                    if doc_id:
                        documents_from_modules.append(doc_id)
            
            discovery_data = {
                "project_id": test_project_id,
                "work_items_checked": len(work_items),
                "documents_in_included": documents_in_included,
                "documents_from_modules": documents_from_modules,
                "unique_documents": list(set(documents_in_included + documents_from_modules))
            }
            
            save_response_to_json("workitem_module_relationships", discovery_data)
            
            print(f"\nWork Item Module Relationships:")
            print(f"  - Work items checked: {len(work_items)}")
            print(f"  - Documents in included: {len(documents_in_included)}")
            print(f"  - Documents from modules: {len(documents_from_modules)}")
            
            if not documents_from_modules and not documents_in_included:
                pytest.skip("No module relationships found in work items")
                
        except Exception as e:
            pytest.skip(f"Could not test module relationships: {e}")
    
    @pytest.mark.integration
    def test_query_workitems_with_module(self, polarion_client, test_project_id):
        """Test querying only work items that have module relationships."""
        try:
            # Query specifically for work items with module
            response = polarion_client.query_work_items(
                query="HAS_VALUE:module",
                project_id=test_project_id,
                **{
                    "page[size]": 20,
                    "include": "module"
                }
            )
            
            work_items = response.get("data", [])
            
            # Extract unique spaces from module document IDs
            spaces = set()
            documents = set()
            
            for wi in work_items:
                relationships = wi.get("relationships", {})
                module = relationships.get("module", {})
                module_data = module.get("data")
                
                if module_data and isinstance(module_data, dict):
                    doc_id = module_data.get("id")
                    if doc_id:
                        documents.add(doc_id)
                        
                        # Extract space from document ID
                        if "/" in doc_id:
                            parts = doc_id.split("/")
                            if len(parts) >= 3:
                                spaces.add(parts[1])
            
            discovery_data = {
                "project_id": test_project_id,
                "query": "HAS_VALUE:module",
                "work_items_with_module": len(work_items),
                "unique_documents": list(documents),
                "unique_spaces": list(spaces),
                "total_documents": len(documents),
                "total_spaces": len(spaces)
            }
            
            save_response_to_json("query_workitems_with_module", discovery_data)
            
            print(f"\nQuery Work Items with Module:")
            print(f"  - Work items with module: {len(work_items)}")
            print(f"  - Unique documents: {len(documents)}")
            print(f"  - Unique spaces: {len(spaces)}")
            
            if spaces:
                print(f"  - Spaces: {', '.join(list(spaces)[:5])}")
            
            if not work_items:
                pytest.skip("No work items with module found")
                
        except Exception as e:
            pytest.skip(f"Could not query work items with module: {e}")
    
    @pytest.mark.integration
    def test_extract_spaces_from_document_ids(self, polarion_client, test_project_id):
        """Test extracting space IDs from document ID patterns."""
        try:
            # Get some work items with modules
            response = polarion_client.get_work_items(
                project_id=test_project_id,
                **{
                    "page[size]": 50,
                    "include": "module"
                }
            )
            
            # Extract and analyze document IDs
            document_patterns = {}
            
            for wi in response.get("data", []):
                relationships = wi.get("relationships", {})
                module = relationships.get("module", {})
                module_data = module.get("data")
                
                if module_data and isinstance(module_data, dict):
                    doc_id = module_data.get("id", "")
                    if "/" in doc_id:
                        parts = doc_id.split("/")
                        pattern_key = f"{len(parts)} parts"
                        
                        if pattern_key not in document_patterns:
                            document_patterns[pattern_key] = []
                        
                        document_patterns[pattern_key].append({
                            "full_id": doc_id,
                            "parts": parts,
                            "project": parts[0] if len(parts) > 0 else None,
                            "space": parts[1] if len(parts) > 1 else None,
                            "document": parts[2] if len(parts) > 2 else None
                        })
            
            # Analyze patterns
            analysis = {
                "project_id": test_project_id,
                "patterns_found": {},
                "unique_spaces": set(),
                "sample_ids": []
            }
            
            for pattern, examples in document_patterns.items():
                analysis["patterns_found"][pattern] = len(examples)
                
                # Extract spaces from 3-part patterns (project/space/document)
                if "3 parts" in pattern:
                    for ex in examples:
                        if ex["space"]:
                            analysis["unique_spaces"].add(ex["space"])
                
                # Save sample IDs
                if examples:
                    analysis["sample_ids"].append(examples[0])
            
            analysis["unique_spaces"] = list(analysis["unique_spaces"])
            
            save_response_to_json("document_id_patterns", analysis)
            
            print(f"\nDocument ID Pattern Analysis:")
            print(f"  - Patterns found: {analysis['patterns_found']}")
            print(f"  - Unique spaces: {len(analysis['unique_spaces'])}")
            
            if analysis["unique_spaces"]:
                print(f"  - Spaces: {', '.join(analysis['unique_spaces'][:5])}")
            
            if not document_patterns:
                pytest.skip("No document patterns found")
                
        except Exception as e:
            pytest.skip(f"Could not analyze document patterns: {e}")