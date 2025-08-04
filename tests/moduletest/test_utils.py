"""
Tests for the utils module.
"""

import pytest
from polarion_api.utils import (
    build_query_params,
    extract_id_parts,
    format_json_api_request,
    parse_json_api_response,
    log_api_call,
    validate_resource_id,
    merge_params
)


class TestUtils:
    """Test utility functions."""
    
    @pytest.mark.unit
    def test_build_query_params_empty(self):
        """Test building query params with empty dict."""
        assert build_query_params({}) == ""
        assert build_query_params(None) == ""
    
    @pytest.mark.unit
    def test_build_query_params_simple(self):
        """Test building query params with simple values."""
        params = {
            "page[size]": 10,
            "sort": "name"
        }
        result = build_query_params(params)
        
        assert result.startswith("?")
        assert "page%5Bsize%5D=10" in result
        assert "sort=name" in result
    
    @pytest.mark.unit
    def test_build_query_params_boolean(self):
        """Test building query params with boolean values."""
        params = {"active": True, "deleted": False}
        result = build_query_params(params)
        
        assert "active=true" in result
        assert "deleted=false" in result
    
    @pytest.mark.unit
    def test_build_query_params_list(self):
        """Test building query params with list values."""
        params = {"fields": ["id", "name", "type"]}
        result = build_query_params(params)
        
        assert "fields=id%2Cname%2Ctype" in result
    
    @pytest.mark.unit
    def test_build_query_params_none_values(self):
        """Test building query params filters out None values."""
        params = {
            "page[size]": 10,
            "sort": None,
            "include": "author"
        }
        result = build_query_params(params)
        
        assert "page%5Bsize%5D=10" in result
        assert "include=author" in result
        assert "sort" not in result
    
    @pytest.mark.unit
    def test_extract_id_parts_work_item(self):
        """Test extracting parts from work item ID."""
        parts = extract_id_parts("myproject/REQ-123")
        
        assert parts["project_id"] == "myproject"
        assert parts["item_id"] == "REQ-123"
    
    @pytest.mark.unit
    def test_extract_id_parts_document(self):
        """Test extracting parts from document ID."""
        parts = extract_id_parts("myproject/_default/requirements")
        
        assert parts["project_id"] == "myproject"
        assert parts["space_id"] == "_default"
        assert parts["document_id"] == "requirements"
    
    @pytest.mark.unit
    def test_extract_id_parts_unknown_format(self):
        """Test extracting parts from unknown ID format."""
        parts = extract_id_parts("single-id")
        
        assert parts["id"] == "single-id"
        assert "project_id" not in parts
    
    @pytest.mark.unit
    def test_format_json_api_request_create(self):
        """Test formatting JSON:API request for creation."""
        result = format_json_api_request(
            resource_type="workitems",
            attributes={"title": "Test", "type": "requirement"},
            relationships={"author": {"data": {"type": "users", "id": "admin"}}}
        )
        
        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1
        
        item = result["data"][0]
        assert item["type"] == "workitems"
        assert item["attributes"]["title"] == "Test"
        assert "relationships" in item
        assert "id" not in item
    
    @pytest.mark.unit
    def test_format_json_api_request_update(self):
        """Test formatting JSON:API request for update."""
        result = format_json_api_request(
            resource_type="workitems",
            attributes={"status": "closed"},
            resource_id="myproject/REQ-123"
        )
        
        assert "data" in result
        assert isinstance(result["data"], dict)  # Not a list for updates
        assert result["data"]["id"] == "myproject/REQ-123"
        assert result["data"]["attributes"]["status"] == "closed"
    
    @pytest.mark.unit
    def test_parse_json_api_response_single(self):
        """Test parsing single resource response."""
        response = {
            "data": {
                "type": "workitems",
                "id": "proj/123",
                "attributes": {"title": "Test"},
                "relationships": {
                    "author": {
                        "data": {"type": "users", "id": "user1"}
                    }
                }
            },
            "included": [
                {
                    "type": "users",
                    "id": "user1",
                    "attributes": {"name": "Test User"}
                }
            ]
        }
        
        result = parse_json_api_response(response)
        
        assert "data" in result
        assert "resolved_relationships" in result["data"]
        assert result["data"]["resolved_relationships"]["author"]["attributes"]["name"] == "Test User"
    
    @pytest.mark.unit
    def test_parse_json_api_response_collection(self):
        """Test parsing collection response."""
        response = {
            "data": [
                {
                    "type": "workitems",
                    "id": "proj/123",
                    "relationships": {
                        "module": {
                            "data": {"type": "documents", "id": "doc1"}
                        }
                    }
                },
                {
                    "type": "workitems",
                    "id": "proj/124"
                }
            ],
            "included": [
                {
                    "type": "documents",
                    "id": "doc1",
                    "attributes": {"title": "Test Doc"}
                }
            ]
        }
        
        result = parse_json_api_response(response)
        
        assert len(result["data"]) == 2
        assert "resolved_relationships" in result["data"][0]
        assert result["data"][0]["resolved_relationships"]["module"]["attributes"]["title"] == "Test Doc"
    
    @pytest.mark.unit
    def test_parse_json_api_response_no_includes(self):
        """Test parsing response without included resources."""
        response = {
            "data": {
                "type": "workitems",
                "id": "proj/123",
                "attributes": {"title": "Test"}
            }
        }
        
        result = parse_json_api_response(response)
        
        assert result == response  # Should return unchanged
    
    @pytest.mark.unit
    def test_validate_resource_id_work_items(self):
        """Test validating work item IDs."""
        assert validate_resource_id("project/item", "workitems") is True
        assert validate_resource_id("project/REQ-123", "workitems") is True
        assert validate_resource_id("single-id", "workitems") is False
        assert validate_resource_id("", "workitems") is False
        assert validate_resource_id("project//item", "workitems") is False
    
    @pytest.mark.unit
    def test_validate_resource_id_documents(self):
        """Test validating document IDs."""
        assert validate_resource_id("project/space/doc", "documents") is True
        assert validate_resource_id("project/_default/requirements", "documents") is True
        assert validate_resource_id("project/doc", "documents") is False
        assert validate_resource_id("single-id", "documents") is False
    
    @pytest.mark.unit
    def test_validate_resource_id_projects(self):
        """Test validating project IDs."""
        assert validate_resource_id("myproject", "projects") is True
        assert validate_resource_id("project-123", "projects") is True
        assert validate_resource_id("project/sub", "projects") is False
        assert validate_resource_id("", "projects") is False
    
    @pytest.mark.unit
    def test_merge_params_empty(self):
        """Test merging empty parameter dicts."""
        assert merge_params() == {}
        assert merge_params(None) == {}
        assert merge_params({}, None, {}) == {}
    
    @pytest.mark.unit
    def test_merge_params_single(self):
        """Test merging single parameter dict."""
        params = {"page[size]": 10, "sort": "name"}
        assert merge_params(params) == params
    
    @pytest.mark.unit
    def test_merge_params_multiple(self):
        """Test merging multiple parameter dicts."""
        params1 = {"page[size]": 10}
        params2 = {"sort": "name"}
        params3 = {"include": "author"}
        
        result = merge_params(params1, params2, params3)
        
        assert result["page[size]"] == 10
        assert result["sort"] == "name"
        assert result["include"] == "author"
    
    @pytest.mark.unit
    def test_merge_params_overwrite(self):
        """Test merging with overwrites."""
        params1 = {"page[size]": 10, "sort": "name"}
        params2 = {"page[size]": 20, "include": "author"}
        
        result = merge_params(params1, params2)
        
        assert result["page[size]"] == 20  # Second value wins
        assert result["sort"] == "name"
        assert result["include"] == "author"
    
    @pytest.mark.unit
    def test_log_api_call(self, caplog):
        """Test API call logging."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        log_api_call(
            method="GET",
            url="https://test.com/api/projects",
            request_data={"test": "data"},
            response_data={"result": "success"},
            status_code=200
        )
        
        # Check log messages
        assert "API Call: GET https://test.com/api/projects" in caplog.text
        assert "Request:" in caplog.text
        assert "Response Status: 200" in caplog.text
        assert "Response:" in caplog.text
    
    @pytest.mark.unit
    def test_log_api_call_large_response(self, caplog):
        """Test API call logging with large response truncation."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        # Create large response
        large_data = {"data": ["x" * 100 for _ in range(20)]}
        
        log_api_call(
            method="GET",
            url="https://test.com/api",
            response_data=large_data,
            status_code=200
        )
        
        # Check that response was truncated
        assert "... (truncated)" in caplog.text