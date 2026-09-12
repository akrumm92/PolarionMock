"""
Documents API endpoints for Polarion Mock Server

The document parts endpoints (GET/POST .../parts) live in document_parts.py.
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Dict, Any, List

from ..models.document import Document
from ..storage.data_store import data_store
from ..utils.response_builder import JSONAPIResponseBuilder
from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError, ValidationError
from ..utils.parts import absolutize_links, base_url_of

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('documents', __name__)

# Initialize response builder
response_builder = JSONAPIResponseBuilder()


@bp.route('/documents/<path:document_id>', methods=['GET'])
@require_auth
def get_document_by_id(document_id: str):
    """Get a document by its full ID."""
    document = data_store.documents.get(document_id)
    if not document:
        raise NotFoundError("documents", document_id)
    
    resource = absolutize_links(document.to_json_api(), base_url_of(request))
    response = response_builder.build_response(data=resource, links={"self": request.url})
    logger.info(f"Retrieved document: {document_id}")
    return jsonify(response)


@bp.route('/all/documents', methods=['GET'])
@require_auth
def list_all_documents():
    """
    This endpoint does not exist in Polarion REST API v1.
    Return 404 to match production behavior.
    """
    return jsonify({
        "errors": [{
            "status": "404",
            "title": "Not Found",
            "detail": "The requested resource [/polarion/rest/v1/all/documents] is not available"
        }]
    }), 404


@bp.route('/projects/<project_id>/documents', methods=['GET'])
@require_auth
def list_project_documents(project_id: str):
    """
    CRITICAL: This endpoint DOES NOT EXIST in Polarion REST API v1.
    Documents are discovered through work item module relationships.
    Return 404 to match production behavior.
    
    From MOCK_IMPLEMENTATION_REQUIREMENTS.md:
    - GET /projects/{projectId}/documents DOES NOT EXIST
    - Documents are discovered via work items' module relationships
    """
    return jsonify({
        "errors": [{
            "status": "404",
            "title": "Not Found",
            "detail": f"The requested resource [/polarion/rest/v1/projects/{project_id}/documents] is not available"
        }]
    }), 404


@bp.route('/projects/<project_id>/spaces', methods=['GET'])
@require_auth
def list_project_spaces(project_id: str):
    """
    CRITICAL: This endpoint DOES NOT EXIST in Polarion REST API v1.
    Spaces are discovered through work item module relationships.
    Return 404 to match production behavior.
    
    From MOCK_IMPLEMENTATION_REQUIREMENTS.md:
    - GET /projects/{projectId}/spaces DOES NOT EXIST
    - Spaces are discovered via work items' module relationships
    """
    return jsonify({
        "errors": [{
            "status": "404",
            "title": "Not Found",
            "detail": f"The requested resource [/polarion/rest/v1/projects/{project_id}/spaces] is not available"
        }]
    }), 404


@bp.route('/projects/<project_id>/spaces/<space_id>/documents', methods=['GET'])
@require_auth
def list_space_documents(project_id: str, space_id: str):
    """
    GET requests to this endpoint are not allowed in Polarion.
    Return 405 Method Not Allowed to match production behavior.
    """
    return jsonify({
        'errors': [{
            'status': '405',
            'title': 'Method Not Allowed',
            'detail': 'GET method is not allowed for this endpoint'
        }]
    }), 405


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_id>', methods=['GET'])
@require_auth
def get_document(project_id: str, space_id: str, document_id: str):
    """Get a specific document."""
    full_id = f"{project_id}/{space_id}/{document_id}"
    
    document = data_store.documents.get(full_id)
    if not document:
        raise NotFoundError("documents", full_id)
    
    # Build response (absolute links like production)
    resource = absolutize_links(document.to_json_api(), base_url_of(request))
    response = response_builder.build_response(data=resource, links={"self": request.url})
    
    logger.info(f"Retrieved document: {full_id}")
    return jsonify(response)


@bp.route('/projects/<project_id>/spaces/<space_id>/documents', methods=['POST'])
@require_auth
def create_documents(project_id: str, space_id: str):
    """Create one or more documents."""
    # Check if project exists
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if not data or 'data' not in data:
        raise ValidationError("Request must contain 'data' array")
    
    if not isinstance(data['data'], list):
        raise ValidationError("'data' must be an array")
    
    created_documents = []
    
    for doc_data in data['data']:
        # Validate document data
        if doc_data.get('type') != 'documents':
            raise ValidationError("Resource type must be 'documents'")
        
        attributes = doc_data.get('attributes', {})
        if 'title' not in attributes:
            raise ValidationError("Document title is required", field="title")
        
        if 'moduleName' not in attributes:
            raise ValidationError("Document module name is required", field="moduleName")
        
        # Create document
        document = Document.create_mock(
            project_id=project_id,
            space_id=space_id,
            document_id=attributes['moduleName'],
            title=attributes['title'],
            type=attributes.get('type', 'generic'),
            status=attributes.get('status', 'draft'),
            homePageContent=attributes.get('homePageContent'),
            structureLinkRole=attributes.get('structureLinkRole', 'parent')
        )
        
        # Check if document already exists
        if document.id in data_store.documents:
            raise ConflictError(f"Document {document.id} already exists")
        
        # Store document
        data_store.documents[document.id] = document
        data_store.document_parts[document.id] = []
        created_documents.append(document)
    
    # Build response
    resources = [doc.to_json_api() for doc in created_documents]
    response = response_builder.build_response(data=resources)
    
    logger.info(f"Created {len(created_documents)} documents in {project_id}/{space_id}")
    return jsonify(response), 201


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_id>', methods=['PATCH'])
@require_auth
def update_document(project_id: str, space_id: str, document_id: str):
    """Update a document."""
    full_id = f"{project_id}/{space_id}/{document_id}"
    
    # Check if document exists
    document = data_store.documents.get(full_id)
    if not document:
        raise NotFoundError("documents", full_id)
    
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if not data or 'data' not in data:
        raise ValidationError("Request must contain 'data' object")
    
    doc_data = data['data']
    
    # Update attributes
    if 'attributes' in doc_data:
        for key, value in doc_data['attributes'].items():
            if hasattr(document.attributes, key):
                setattr(document.attributes, key, value)
        
        document.attributes.updated = datetime.utcnow()
    
    # Build response
    response = response_builder.build_response(data=document.to_json_api())
    
    logger.info(f"Updated document: {full_id}")
    return jsonify(response)


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_id>', methods=['DELETE'])
@require_auth
def delete_document(project_id: str, space_id: str, document_id: str):
    """Delete a document."""
    full_id = f"{project_id}/{space_id}/{document_id}"
    
    if full_id not in data_store.documents:
        raise NotFoundError("documents", full_id)
    
    # Remove document parts
    if full_id in data_store.document_parts:
        del data_store.document_parts[full_id]
    
    # Remove module relationships from work items
    for workitem in data_store.workitems.values():
        if (workitem.relationships and 
            'module' in workitem.relationships and
            workitem.relationships['module']['data']['id'] == full_id):
            del workitem.relationships['module']
    
    # Delete document
    del data_store.documents[full_id]
    
    logger.info(f"Deleted document: {full_id}")
    return '', 204


@bp.route('/documents/<path:document_id>/workitems', methods=['GET'])
@require_auth
def list_document_workitems(document_id: str):
    """List work items in a document."""
    # Check if document exists
    if document_id not in data_store.documents:
        raise NotFoundError("documents", document_id)
    
    # Query work items that belong to this document
    workitems = data_store.query_workitems(query=f"module.id:{document_id}")
    
    # Convert to JSON:API format
    resources = [wi.to_json_api() for wi in workitems]
    
    response = response_builder.build_collection_response(
        resources=resources,
        total_count=len(resources),
        page_number=1,
        page_size=100
    )
    
    logger.info(f"Listed {len(resources)} work items for document {document_id}")
    return jsonify(response)


# Import to fix circular import issues
from datetime import datetime
from ..middleware.error_handler import ConflictError