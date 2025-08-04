"""
Documents API endpoints for Polarion Mock Server
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Dict, Any, List

from ..models.document import Document
from ..storage.data_store import data_store
from ..utils.response_builder import JSONAPIResponseBuilder
from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError, ValidationError

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
    
    response = response_builder.build_response(data=document.to_json_api())
    logger.info(f"Retrieved document: {document_id}")
    return jsonify(response)


@bp.route('/all/documents', methods=['GET'])
@require_auth
def list_all_documents():
    """List all documents across all projects."""
    # Get query parameters
    page_size = int(request.args.get('page[size]', 100))
    page_number = int(request.args.get('page[number]', 1))
    
    # Get all documents
    all_documents = list(data_store.documents.values())
    
    # Apply sorting
    sort_param = request.args.get('sort')
    if sort_param:
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        
        if sort_field == 'created':
            all_documents.sort(key=lambda d: d.attributes.created, reverse=reverse)
        elif sort_field == 'title':
            all_documents.sort(key=lambda d: d.attributes.title, reverse=reverse)
        elif sort_field == 'name':
            all_documents.sort(key=lambda d: d.attributes.name, reverse=reverse)
    
    # Pagination
    total_count = len(all_documents)
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    documents_page = all_documents[start_idx:end_idx]
    
    # Convert to JSON:API format
    resources = [doc.to_json_api() for doc in documents_page]
    
    # Build response
    response = response_builder.build_collection_response(
        resources=resources,
        total_count=total_count,
        page_number=page_number,
        page_size=page_size
    )
    
    logger.info(f"Listed {len(resources)} documents total")
    return jsonify(response)


@bp.route('/projects/<project_id>/spaces/<space_id>/documents', methods=['GET'])
@require_auth
def list_space_documents(project_id: str, space_id: str):
    """List documents in a specific space."""
    # Check if project exists
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    
    # Filter documents by project and space
    space_prefix = f"{project_id}/{space_id}/"
    space_documents = [
        doc for doc in data_store.documents.values()
        if doc.id.startswith(space_prefix)
    ]
    
    # Get query parameters
    page_size = int(request.args.get('page[size]', 100))
    page_number = int(request.args.get('page[number]', 1))
    
    # Pagination
    total_count = len(space_documents)
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    documents_page = space_documents[start_idx:end_idx]
    
    # Convert to JSON:API format
    resources = [doc.to_json_api() for doc in documents_page]
    
    # Build response
    response = response_builder.build_collection_response(
        resources=resources,
        total_count=total_count,
        page_number=page_number,
        page_size=page_size
    )
    
    logger.info(f"Listed {len(resources)} documents in space {project_id}/{space_id}")
    return jsonify(response)


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_id>', methods=['GET'])
@require_auth
def get_document(project_id: str, space_id: str, document_id: str):
    """Get a specific document."""
    full_id = f"{project_id}/{space_id}/{document_id}"
    
    document = data_store.documents.get(full_id)
    if not document:
        raise NotFoundError("documents", full_id)
    
    # Build response
    response = response_builder.build_response(data=document.to_json_api())
    
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


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_id>/parts', methods=['GET'])
@require_auth
def list_document_parts(project_id: str, space_id: str, document_id: str):
    """List document parts (structured content)."""
    full_id = f"{project_id}/{space_id}/{document_id}"
    
    # Check if document exists
    if full_id not in data_store.documents:
        raise NotFoundError("documents", full_id)
    
    # Get document parts
    parts = data_store.document_parts.get(full_id, [])
    
    # Include work items if requested
    include = request.args.get('include', '').split(',') if request.args.get('include') else []
    included = []
    
    if 'workItem' in include:
        for part in parts:
            if (part.get('attributes', {}).get('type') == 'workitem' and
                'workItem' in part.get('relationships', {})):
                workitem_id = part['relationships']['workItem']['data']['id']
                if workitem_id in data_store.workitems:
                    included.append(data_store.workitems[workitem_id].to_json_api())
    
    # Build response
    response = response_builder.build_response(
        data=parts,
        included=included if included else None
    )
    
    logger.info(f"Listed {len(parts)} parts for document {full_id}")
    return jsonify(response)


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


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_id>/parts', methods=['POST'])
@require_auth
def create_document_part(project_id: str, space_id: str, document_id: str):
    """Add a part to document (e.g., work item)."""
    full_id = f"{project_id}/{space_id}/{document_id}"
    
    # Check if document exists
    if full_id not in data_store.documents:
        raise NotFoundError("documents", full_id)
    
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if not data or 'data' not in data:
        raise ValidationError("Request must contain 'data' array")
    
    if not isinstance(data['data'], list):
        raise ValidationError("'data' must be an array")
    
    created_parts = []
    
    for part_data in data['data']:
        # Validate part data
        if part_data.get('type') != 'document_parts':
            raise ValidationError("Resource type must be 'document_parts'")
        
        attributes = part_data.get('attributes', {})
        part_type = attributes.get('type')
        
        if part_type == 'workitem':
            # Validate work item relationship
            relationships = part_data.get('relationships', {})
            if 'workItem' not in relationships:
                raise ValidationError("workItem relationship is required for workitem parts")
            
            workitem_id = relationships['workItem']['data']['id']
            if workitem_id not in data_store.workitems:
                raise NotFoundError("workitems", workitem_id)
            
            # Update work item module relationship
            workitem = data_store.workitems[workitem_id]
            if not workitem.relationships:
                workitem.relationships = {}
            workitem.relationships['module'] = {
                'data': {
                    'type': 'documents',
                    'id': full_id
                }
            }
        
        # Create part ID
        part_num = len(data_store.document_parts.get(full_id, [])) + 1
        part_id = f"{full_id}/part_{part_num}"
        
        # Create part
        part = {
            'type': 'document_parts',
            'id': part_id,
            'attributes': attributes,
            'relationships': part_data.get('relationships', {})
        }
        
        # Add to document parts
        if full_id not in data_store.document_parts:
            data_store.document_parts[full_id] = []
        data_store.document_parts[full_id].append(part)
        created_parts.append(part)
    
    # Build response
    response = response_builder.build_response(data=created_parts)
    
    logger.info(f"Created {len(created_parts)} parts in document {full_id}")
    return jsonify(response), 201


# Import to fix circular import issues
from datetime import datetime
from ..middleware.error_handler import ConflictError