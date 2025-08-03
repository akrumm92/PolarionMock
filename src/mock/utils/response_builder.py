"""
JSON:API Response Builder for Polarion Mock Server
Builds compliant JSON:API responses
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from flask import request, url_for


class JSONAPIResponseBuilder:
    """Builder for JSON:API compliant responses."""
    
    def __init__(self):
        self.base_url = '/polarion/rest/v1'
    
    def build_resource_identifier(self, resource_type: str, resource_id: str) -> Dict[str, str]:
        """Build a resource identifier object."""
        return {
            'type': resource_type,
            'id': resource_id
        }
    
    def build_resource_object(
        self,
        resource_type: str,
        resource_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        relationships: Optional[Dict[str, Any]] = None,
        links: Optional[Dict[str, str]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a complete resource object."""
        resource = self.build_resource_identifier(resource_type, resource_id)
        
        if attributes:
            resource['attributes'] = attributes
        
        if relationships:
            resource['relationships'] = relationships
        
        if links:
            resource['links'] = links
        else:
            # Generate default self link
            resource['links'] = {
                'self': f"{self.base_url}/{resource_type}/{resource_id}"
            }
        
        if meta:
            resource['meta'] = meta
        
        return resource
    
    def build_relationship(
        self,
        data: Union[Dict[str, str], List[Dict[str, str]], None],
        links: Optional[Dict[str, str]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a relationship object."""
        relationship = {}
        
        if data is not None:
            relationship['data'] = data
        
        if links:
            relationship['links'] = links
        
        if meta:
            relationship['meta'] = meta
        
        return relationship
    
    def build_response(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]], None] = None,
        included: Optional[List[Dict[str, Any]]] = None,
        meta: Optional[Dict[str, Any]] = None,
        links: Optional[Dict[str, str]] = None,
        jsonapi: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a complete JSON:API response."""
        response = {}
        
        if data is not None:
            response['data'] = data
        
        if included:
            response['included'] = included
        
        if meta:
            response['meta'] = meta
        
        if links:
            response['links'] = links
        
        if jsonapi:
            response['jsonapi'] = jsonapi
        else:
            response['jsonapi'] = {'version': '1.0'}
        
        return response
    
    def build_collection_response(
        self,
        resources: List[Dict[str, Any]],
        total_count: Optional[int] = None,
        page_number: int = 1,
        page_size: int = 100,
        included: Optional[List[Dict[str, Any]]] = None,
        links: Optional[Dict[str, str]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a collection response with pagination."""
        # Calculate pagination
        if total_count is None:
            total_count = len(resources)
        
        total_pages = (total_count + page_size - 1) // page_size
        
        # Build pagination links
        if not links:
            links = self._build_pagination_links(page_number, total_pages, page_size)
        
        # Build meta with pagination info
        if not meta:
            meta = {}
        
        meta.update({
            'totalCount': total_count,
            'pageCount': len(resources),
            'currentPage': page_number,
            'pageSize': page_size,
            'totalPages': total_pages
        })
        
        return self.build_response(
            data=resources,
            included=included,
            meta=meta,
            links=links
        )
    
    def _build_pagination_links(
        self,
        page_number: int,
        total_pages: int,
        page_size: int
    ) -> Dict[str, str]:
        """Build pagination links."""
        base_url = request.base_url
        links = {
            'self': f"{base_url}?page[number]={page_number}&page[size]={page_size}",
            'first': f"{base_url}?page[number]=1&page[size]={page_size}",
            'last': f"{base_url}?page[number]={total_pages}&page[size]={page_size}"
        }
        
        if page_number > 1:
            links['prev'] = f"{base_url}?page[number]={page_number - 1}&page[size]={page_size}"
        
        if page_number < total_pages:
            links['next'] = f"{base_url}?page[number]={page_number + 1}&page[size]={page_size}"
        
        return links
    
    def build_error_response(
        self,
        errors: List[Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build an error response."""
        response = {'errors': errors}
        
        if meta:
            response['meta'] = meta
        
        return response
    
    def format_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Format datetime to ISO 8601 string."""
        if dt:
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return None
    
    def parse_sparse_fieldsets(self, fields_param: Optional[str]) -> Optional[List[str]]:
        """Parse sparse fieldsets parameter."""
        if fields_param:
            return [f.strip() for f in fields_param.split(',')]
        return None
    
    def parse_include_param(self, include_param: Optional[str]) -> Optional[List[str]]:
        """Parse include parameter."""
        if include_param:
            return [i.strip() for i in include_param.split(',')]
        return None
    
    def apply_sparse_fieldsets(
        self,
        resource: Dict[str, Any],
        fields: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Apply sparse fieldsets to a resource."""
        if not fields or 'attributes' not in resource:
            return resource
        
        # Filter attributes
        filtered_attributes = {}
        for field in fields:
            if field in resource['attributes']:
                filtered_attributes[field] = resource['attributes'][field]
        
        resource['attributes'] = filtered_attributes
        return resource