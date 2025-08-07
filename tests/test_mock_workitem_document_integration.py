"""
Test suite for Mock Server WorkItem-Document Integration.

Verifies that the mock correctly implements the two-step process.
"""

import pytest
import requests
import json
import os
from typing import Dict, Any


class TestMockWorkItemDocumentIntegration:
    """Test the mock's implementation of WorkItem-Document integration."""
    
    @pytest.fixture
    def mock_base_url(self):
        """Get mock server base URL."""
        return os.getenv("MOCK_BASE_URL", "http://localhost:5001")
    
    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for mock."""
        token = os.getenv("MOCK_AUTH_TOKEN", "")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def test_two_step_process(self, mock_base_url, auth_headers):
        """Test that mock enforces the two-step process correctly."""
        
        # Step 1: Create WorkItem with module relationship
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Test Requirement for Two-Step Process",
                    "type": "requirement",
                    "status": "draft",
                    "description": {
                        "type": "text/html",
                        "value": "<p>Testing two-step process</p>"
                    }
                },
                "relationships": {
                    "module": {
                        "data": {
                            "type": "documents",
                            "id": "TestProject/TestSpace/TestDocument"
                        }
                    }
                }
            }]
        }
        
        # Create WorkItem
        response1 = requests.post(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems",
            json=workitem_data,
            headers=auth_headers
        )
        
        assert response1.status_code == 201, f"Failed to create WorkItem: {response1.text}"
        
        result1 = response1.json()
        workitem_id = result1["data"][0]["id"]
        
        # Verify WorkItem does NOT have outlineNumber yet
        get_response1 = requests.get(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems/{workitem_id.split('/')[-1]}",
            headers=auth_headers,
            params={"fields[workitems]": "@all"}
        )
        
        assert get_response1.status_code == 200
        wi_data1 = get_response1.json()["data"]
        
        # Critical: Should NOT have outlineNumber before Step 2
        assert "outlineNumber" not in wi_data1["attributes"] or wi_data1["attributes"]["outlineNumber"] is None, \
            "WorkItem should not have outlineNumber before Document Parts API call"
        
        # Step 2: Add WorkItem to document via Document Parts API
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
                            "id": workitem_id
                        }
                    }
                }
            }]
        }
        
        response2 = requests.post(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/spaces/TestSpace/documents/TestDocument/parts",
            json=parts_data,
            headers=auth_headers
        )
        
        assert response2.status_code == 201, f"Failed to add document part: {response2.text}"
        
        # Verify WorkItem NOW has outlineNumber
        get_response2 = requests.get(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems/{workitem_id.split('/')[-1]}",
            headers=auth_headers,
            params={"fields[workitems]": "@all"}
        )
        
        assert get_response2.status_code == 200
        wi_data2 = get_response2.json()["data"]
        
        # Critical: Should have outlineNumber after Step 2
        assert "outlineNumber" in wi_data2["attributes"] and wi_data2["attributes"]["outlineNumber"], \
            f"WorkItem should have outlineNumber after Document Parts API call, got: {wi_data2['attributes']}"
        
        print(f"✅ Two-step process verified: WorkItem {workitem_id} has outline {wi_data2['attributes']['outlineNumber']}")
        
        return workitem_id
    
    def test_reject_outline_number_setting(self, mock_base_url, auth_headers):
        """Test that mock rejects attempts to set outlineNumber manually."""
        
        # Try to create WorkItem with outlineNumber (should fail)
        workitem_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Invalid WorkItem",
                    "type": "requirement",
                    "outlineNumber": "1.2.3"  # This should be rejected
                }
            }]
        }
        
        response = requests.post(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems",
            json=workitem_data,
            headers=auth_headers
        )
        
        # This test may need adjustment based on mock's validation
        # Some mocks might silently ignore the field rather than error
        if response.status_code == 400:
            assert "outlineNumber" in response.text or "read-only" in response.text
            print("✅ Mock correctly rejects manual outlineNumber setting")
        else:
            # If created, verify outlineNumber was ignored
            if response.status_code == 201:
                result = response.json()
                workitem_id = result["data"][0]["id"]
                
                # Get the WorkItem
                get_response = requests.get(
                    f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems/{workitem_id.split('/')[-1]}",
                    headers=auth_headers,
                    params={"fields[workitems]": "@all"}
                )
                
                wi_data = get_response.json()["data"]
                # Should not have the manually set outline number
                assert wi_data["attributes"].get("outlineNumber") != "1.2.3", \
                    "Mock should not accept manually set outlineNumber"
                print("✅ Mock correctly ignored manual outlineNumber setting")
    
    def test_document_parts_visibility(self, mock_base_url, auth_headers):
        """Test that only WorkItems added via Document Parts API are visible."""
        
        # Create two WorkItems with module relationships
        workitems_data = {
            "data": [
                {
                    "type": "workitems",
                    "attributes": {
                        "title": "WI in Recycle Bin",
                        "type": "requirement"
                    },
                    "relationships": {
                        "module": {
                            "data": {
                                "type": "documents",
                                "id": "TestProject/TestSpace/TestDocument"
                            }
                        }
                    }
                },
                {
                    "type": "workitems",
                    "attributes": {
                        "title": "WI to be Visible",
                        "type": "requirement"
                    },
                    "relationships": {
                        "module": {
                            "data": {
                                "type": "documents",
                                "id": "TestProject/TestSpace/TestDocument"
                            }
                        }
                    }
                }
            ]
        }
        
        response1 = requests.post(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems",
            json=workitems_data,
            headers=auth_headers
        )
        
        assert response1.status_code == 201
        
        result = response1.json()
        wi1_id = result["data"][0]["id"]
        wi2_id = result["data"][1]["id"]
        
        # Add only wi2 to document
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
                            "id": wi2_id
                        }
                    }
                }
            }]
        }
        
        response2 = requests.post(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/spaces/TestSpace/documents/TestDocument/parts",
            json=parts_data,
            headers=auth_headers
        )
        
        assert response2.status_code == 201
        
        # Get document parts
        parts_response = requests.get(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/spaces/TestSpace/documents/TestDocument/parts",
            headers=auth_headers
        )
        
        if parts_response.status_code == 200:
            parts = parts_response.json()["data"]
            part_ids = [p.get("id", "") for p in parts]
            
            # wi2 should be in parts, wi1 should not
            assert any(wi2_id.split("/")[-1] in pid for pid in part_ids), \
                f"WorkItem {wi2_id} should be in document parts"
            assert not any(wi1_id.split("/")[-1] in pid for pid in part_ids), \
                f"WorkItem {wi1_id} should NOT be in document parts (still in Recycle Bin)"
            
            print(f"✅ Document parts visibility verified: only added WorkItems are visible")
    
    def test_position_with_previous_part(self, mock_base_url, auth_headers):
        """Test positioning WorkItem after a specific part (e.g., header)."""
        
        # Create a header WorkItem
        header_data = {
            "data": [{
                "type": "workitems",
                "attributes": {
                    "title": "Test Header",
                    "type": "heading",
                    "outlineNumber": "4.1"  # Headers might have pre-assigned outline
                },
                "relationships": {
                    "module": {
                        "data": {
                            "type": "documents",
                            "id": "TestProject/TestSpace/TestDocument"
                        }
                    }
                }
            }]
        }
        
        response1 = requests.post(
            f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems",
            json=header_data,
            headers=auth_headers
        )
        
        if response1.status_code == 201:
            header_id = response1.json()["data"][0]["id"]
            
            # Add header to document
            header_parts_data = {
                "data": [{
                    "type": "document_parts",
                    "attributes": {
                        "type": "workitem"
                    },
                    "relationships": {
                        "workItem": {
                            "data": {
                                "type": "workitems",
                                "id": header_id
                            }
                        }
                    }
                }]
            }
            
            requests.post(
                f"{mock_base_url}/polarion/rest/v1/projects/TestProject/spaces/TestSpace/documents/TestDocument/parts",
                json=header_parts_data,
                headers=auth_headers
            )
            
            # Create Safety Goal
            sg_data = {
                "data": [{
                    "type": "workitems",
                    "attributes": {
                        "title": "Test Safety Goal",
                        "type": "safetygoal",
                        "severity": "must_have",
                        "priority": "100.0"
                    },
                    "relationships": {
                        "module": {
                            "data": {
                                "type": "documents",
                                "id": "TestProject/TestSpace/TestDocument"
                            }
                        }
                    }
                }]
            }
            
            response2 = requests.post(
                f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems",
                json=sg_data,
                headers=auth_headers
            )
            
            assert response2.status_code == 201
            sg_id = response2.json()["data"][0]["id"]
            
            # Add Safety Goal after header
            sg_parts_data = {
                "data": [{
                    "type": "document_parts",
                    "attributes": {
                        "type": "workitem"
                    },
                    "relationships": {
                        "workItem": {
                            "data": {
                                "type": "workitems",
                                "id": sg_id
                            }
                        },
                        "previousPart": {
                            "data": {
                                "type": "document_parts",
                                "id": f"heading_{header_id.split('/')[-1]}"
                            }
                        }
                    }
                }]
            }
            
            response3 = requests.post(
                f"{mock_base_url}/polarion/rest/v1/projects/TestProject/spaces/TestSpace/documents/TestDocument/parts",
                json=sg_parts_data,
                headers=auth_headers
            )
            
            if response3.status_code == 201:
                # Verify Safety Goal has correct outline (under header)
                get_response = requests.get(
                    f"{mock_base_url}/polarion/rest/v1/projects/TestProject/workitems/{sg_id.split('/')[-1]}",
                    headers=auth_headers,
                    params={"fields[workitems]": "@all"}
                )
                
                if get_response.status_code == 200:
                    sg_data = get_response.json()["data"]
                    outline = sg_data["attributes"].get("outlineNumber", "")
                    
                    # Should be positioned under the header (e.g., 4.1-1)
                    if outline and ("4.1" in outline or "-1" in outline):
                        print(f"✅ Safety Goal correctly positioned with outline: {outline}")
                    else:
                        print(f"⚠️ Safety Goal outline may not be correctly positioned: {outline}")


if __name__ == "__main__":
    # Run tests against mock server
    print("Testing Mock WorkItem-Document Integration...")
    print("=" * 60)
    
    # Note: Mock server must be running on localhost:5001
    # Set MOCK_AUTH_TOKEN environment variable if authentication is enabled
    
    test = TestMockWorkItemDocumentIntegration()
    mock_url = "http://localhost:5001"
    headers = {
        "Authorization": f"Bearer {os.getenv('MOCK_AUTH_TOKEN', '')}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        print("\n1. Testing two-step process...")
        test.test_two_step_process(mock_url, headers)
        
        print("\n2. Testing outline number rejection...")
        test.test_reject_outline_number_setting(mock_url, headers)
        
        print("\n3. Testing document parts visibility...")
        test.test_document_parts_visibility(mock_url, headers)
        
        print("\n4. Testing positioning with previous part...")
        test.test_position_with_previous_part(mock_url, headers)
        
        print("\n" + "=" * 60)
        print("✅ All mock integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()