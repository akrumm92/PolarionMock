"""
Work Items API endpoints for Polarion Mock Server
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Dict, Any, List
from datetime import datetime

from ..models.workitem import WorkItem
from ..storage.data_store import data_store
from ..utils.response_builder import JSONAPIResponseBuilder
from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError, ValidationError, ConflictError

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('workitems', __name__)

# Initialize response builder
response_builder = JSONAPIResponseBuilder()


@bp.route('/projects/<project_id>/workitems', methods=['GET'])
@require_auth
def list_project_workitems(project_id: str):
    """List work items for a specific project."""
    # Check if project exists
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    
    # Get query parameters
    query = request.args.get('query')
    page_size = int(request.args.get('page[size]', 100))
    page_number = int(request.args.get('page[number]', 1))
    include = request.args.get('include', '').split(',') if request.args.get('include') else []
    
    # Query work items
    workitems = data_store.query_workitems(query=query, project_id=project_id)
    
    # Apply sorting
    sort_param = request.args.get('sort')
    if sort_param:
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        
        if sort_field == 'created':
            workitems.sort(key=lambda w: w.attributes.created, reverse=reverse)
        elif sort_field == 'updated':
            workitems.sort(key=lambda w: w.attributes.updated, reverse=reverse)
        elif sort_field == 'title':
            workitems.sort(key=lambda w: w.attributes.title, reverse=reverse)
    
    # Pagination - ensure page_size is capped at 100
    page_size = min(page_size, 100)
    total_count = len(workitems)
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    workitems_page = workitems[start_idx:end_idx]
    
    # Convert to JSON:API format
    resources = [wi.to_json_api() for wi in workitems_page]
    
    # Handle includes
    included = []
    if 'module' in include:
        for wi in workitems_page:
            if wi.relationships and 'module' in wi.relationships:
                module_id = wi.relationships['module']['data']['id']
                if module_id in data_store.documents:
                    included.append(data_store.documents[module_id].to_json_api())
    
    # Build response with proper pagination links
    base_url = request.base_url
    
    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    has_next = page_number < total_pages
    has_prev = page_number > 1
    
    # Build links with all original query parameters
    def build_page_url(page_num):
        params = request.args.to_dict()
        params['page[number]'] = str(page_num)
        param_str = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{param_str}"
    
    links = {
        'self': request.url,
        'first': build_page_url(1),
        'last': build_page_url(total_pages),
        'next': build_page_url(page_number + 1) if has_next else None,
        'prev': build_page_url(page_number - 1) if has_prev else None,
        'portal': f"https://polarion.example.com/polarion/#/project/{project_id}/workitems"
    }
    
    # Build response
    response = {
        'links': links,
        'data': resources
    }
    
    if included:
        response['included'] = included
    
    logger.info(f"Listed {len(resources)} work items for project {project_id} (page {page_number}/{total_pages})")
    return jsonify(response)


@bp.route('/all/workitems', methods=['GET'])
@require_auth
def list_all_workitems():
    """List all work items across all projects."""
    # Get query parameters
    query = request.args.get('query')
    page_size = int(request.args.get('page[size]', 100))
    page_number = int(request.args.get('page[number]', 1))
    
    # Query all work items
    workitems = data_store.query_workitems(query=query)
    
    # Pagination - ensure page_size is capped at 100
    page_size = min(page_size, 100)
    total_count = len(workitems)
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    workitems_page = workitems[start_idx:end_idx]
    
    # Convert to JSON:API format
    resources = [wi.to_json_api() for wi in workitems_page]
    
    # Build response
    response = response_builder.build_collection_response(
        resources=resources,
        total_count=total_count,
        page_number=page_number,
        page_size=page_size
    )
    
    logger.info(f"Listed {len(resources)} work items total")
    return jsonify(response)


@bp.route('/projects/<project_id>/workitems/<workitem_id>', methods=['GET'])
@require_auth
def get_workitem(project_id: str, workitem_id: str):
    """Get a specific work item."""
    full_id = f"{project_id}/{workitem_id}"
    
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    
    # Build response
    response = response_builder.build_response(data=workitem.to_json_api())
    
    logger.info(f"Retrieved work item: {full_id}")
    return jsonify(response)


@bp.route('/projects/<project_id>/workitems', methods=['POST'])
@require_auth
def create_workitems(project_id: str):
    """Create one or more work items."""
    # Check if project exists
    project = data_store.projects.get_by_id(project_id)
    if not project:
        raise NotFoundError("projects", project_id)
    
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if not data or 'data' not in data:
        raise ValidationError("Request must contain 'data' array")
    
    if not isinstance(data['data'], list):
        raise ValidationError("'data' must be an array")
    
    created_workitems = []
    
    for item_data in data['data']:
        # Validate work item data
        if item_data.get('type') != 'workitems':
            raise ValidationError("Resource type must be 'workitems'")
        
        attributes = item_data.get('attributes', {})
        if 'title' not in attributes:
            raise ValidationError("Work item title is required", field="title")
        
        # Generate work item ID if not provided
        if 'id' in item_data:
            workitem_id = item_data['id']
        else:
            workitem_id = data_store.get_next_workitem_id(project_id)
        
        # Create work item
        workitem = WorkItem.create_mock(
            project_id=project_id,
            workitem_id=workitem_id,
            title=attributes['title'],
            type=attributes.get('type', 'task'),
            description=attributes.get('description'),
            status=attributes.get('status', 'open'),
            priority=attributes.get('priority', 'medium'),
            severity=attributes.get('severity'),
            author=getattr(g, 'current_user', {}).get('user_id', 'admin'),
            assignee=attributes.get('assignee')
        )
        
        # Handle relationships
        if 'relationships' in item_data:
            workitem.relationships = item_data['relationships']
            
            # CRITICAL: Do NOT automatically add to document when module relationship exists
            # This follows Polarion's two-step process - WorkItem goes to "Recycle Bin"
            # Must use Document Parts API to make it visible
            if 'module' in item_data['relationships']:
                module_id = item_data['relationships']['module']['data']['id']
                if module_id in data_store.documents:
                    # Mark as in recycle bin - has module but not in document
                    workitem._in_recycle_bin = True
                    workitem._is_in_document = False
                    logger.info(f"Work item {workitem.id} linked to module {module_id} (in Recycle Bin)")
                else:
                    logger.warning(f"Document {module_id} not found for work item {workitem.id}")
        
        # Store work item
        data_store.workitems[workitem.id] = workitem
        created_workitems.append(workitem)
    
    # Build response
    resources = [wi.to_json_api() for wi in created_workitems]
    response = response_builder.build_response(data=resources)
    
    logger.info(f"Created {len(created_workitems)} work items in project {project_id}")
    return jsonify(response), 201


@bp.route('/projects/<project_id>/workitems/<workitem_id>', methods=['PATCH'])
@require_auth
def update_workitem(project_id: str, workitem_id: str):
    """Update a work item."""
    full_id = f"{project_id}/{workitem_id}"
    
    # Check if work item exists
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if not data or 'data' not in data:
        raise ValidationError("Request must contain 'data' object")
    
    item_data = data['data']
    
    # Update attributes
    if 'attributes' in item_data:
        for key, value in item_data['attributes'].items():
            # Handle special relationship fields in attributes
            if key == 'parentWorkItemId':
                # Convert to relationship format
                if not workitem.relationships:
                    workitem.relationships = {}
                workitem.relationships['parent'] = {
                    'data': {
                        'type': 'workitems',
                        'id': value
                    }
                }
            elif hasattr(workitem.attributes, key):
                setattr(workitem.attributes, key, value)
        
        workitem.attributes.updated = datetime.utcnow()
    
    # Update relationships
    if 'relationships' in item_data:
        if not workitem.relationships:
            workitem.relationships = {}
        
        # Update each relationship
        for rel_name, rel_data in item_data['relationships'].items():
            workitem.relationships[rel_name] = rel_data
    
    # Polarion returns 204 No Content for PATCH requests
    logger.info(f"Updated work item: {full_id}")
    return '', 204


@bp.route('/projects/<project_id>/workitems/<workitem_id>', methods=['DELETE'])
@require_auth
def delete_workitem(project_id: str, workitem_id: str):
    """Delete a work item."""
    full_id = f"{project_id}/{workitem_id}"
    
    if full_id not in data_store.workitems:
        raise NotFoundError("workitems", full_id)
    
    # Remove from document parts if it has a module relationship
    workitem = data_store.workitems[full_id]
    if workitem.relationships and 'module' in workitem.relationships:
        module_id = workitem.relationships['module']['data']['id']
        if module_id in data_store.document_parts:
            data_store.document_parts[module_id] = [
                part for part in data_store.document_parts[module_id]
                if part['relationships']['workItem']['data']['id'] != full_id
            ]
    
    # Delete work item
    del data_store.workitems[full_id]
    
    logger.info(f"Deleted work item: {full_id}")
    return '', 204


@bp.route('/projects/<project_id>/workitems/<workitem_id>/linkedworkitems', methods=['GET'])
@require_auth
def list_linked_workitems(project_id: str, workitem_id: str):
    """List linked work items."""
    full_id = f"{project_id}/{workitem_id}"
    
    # Check if work item exists
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    
    # Get linked work items
    linked_items = []
    if hasattr(workitem, 'linkedWorkItems'):
        linked_items = workitem.linkedWorkItems
    
    return jsonify({
        'data': linked_items,
        'links': {
            'self': request.url
        }
    })


@bp.route('/projects/<project_id>/workitems/<workitem_id>/linkedworkitems', methods=['POST'])
@require_auth
def create_linked_workitem(project_id: str, workitem_id: str):
    """Create a link between work items."""
    full_id = f"{project_id}/{workitem_id}"
    
    # Check if work item exists
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    
    # Get request data
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if 'data' not in data or not isinstance(data['data'], list):
        raise ValidationError("Request must contain 'data' array")
    
    created_links = []
    for link_data in data['data']:
        if link_data.get('type') != 'linkedworkitems':
            raise ValidationError("Invalid type, expected 'linkedworkitems'")
        
        # Get role and target work item
        role = link_data.get('attributes', {}).get('role', 'relates_to')
        target_wi = link_data.get('relationships', {}).get('workItem', {}).get('data', {})
        target_id = target_wi.get('id')
        
        if not target_id:
            raise ValidationError("Target work item ID is required")
        
        # Check if target work item exists
        if target_id not in data_store.workitems:
            raise NotFoundError("workitems", target_id)
        
        # Initialize linkedWorkItems if not exists
        if not hasattr(workitem, 'linkedWorkItems'):
            workitem.linkedWorkItems = []
        
        # Check if link already exists
        existing_link = next((l for l in workitem.linkedWorkItems 
                             if l.get('role') == role and 
                             l.get('workItem', {}).get('id') == target_id), None)
        
        if existing_link:
            raise ConflictError(f"Link with role '{role}' to {target_id} already exists")
        
        # Create the link
        link = {
            'type': 'linkedworkitems',
            'id': f"{full_id}/{role}/{target_id}",
            'attributes': {
                'role': role,
                'suspect': link_data.get('attributes', {}).get('suspect', False)
            },
            'relationships': {
                'workItem': {
                    'data': {
                        'type': 'workitems',
                        'id': target_id
                    }
                }
            }
        }
        
        workitem.linkedWorkItems.append(link)
        created_links.append(link)
        
        logger.info(f"Created link: {full_id} --[{role}]--> {target_id}")
    
    return jsonify({'data': created_links}), 201


@bp.route('/projects/<project_id>/workitems/<workitem_id>/linkedworkitems/<role>/<path:target_id>', methods=['DELETE'])
@require_auth
def delete_linked_workitem(project_id: str, workitem_id: str, role: str, target_id: str):
    """Delete a link between work items."""
    full_id = f"{project_id}/{workitem_id}"
    
    # Check if work item exists
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    
    # Find and remove the link
    if hasattr(workitem, 'linkedWorkItems'):
        original_count = len(workitem.linkedWorkItems)
        workitem.linkedWorkItems = [
            l for l in workitem.linkedWorkItems
            if not (l.get('attributes', {}).get('role') == role and
                   l.get('relationships', {}).get('workItem', {}).get('data', {}).get('id') == target_id)
        ]
        
        if len(workitem.linkedWorkItems) < original_count:
            logger.info(f"Deleted link: {full_id} --[{role}]-X-> {target_id}")
            return '', 204
    
    # Link not found
    raise NotFoundError("linkedworkitems", f"{role}/{target_id}")


@bp.route('/projects/<project_id>/workitems/<workitem_id>/actions/moveToDocument', methods=['POST'])
@require_auth
def move_workitem_to_document(project_id: str, workitem_id: str):
    """Move a work item to a document."""
    full_id = f"{project_id}/{workitem_id}"
    
    # Check if work item exists
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    
    # Get request data
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    target_document = data.get('targetDocument')
    
    if not target_document:
        raise ValidationError("targetDocument is required")
    
    # Check if document exists
    if target_document not in data_store.documents:
        raise NotFoundError("documents", target_document)
    
    # Update work item module relationship
    if not workitem.relationships:
        workitem.relationships = {}
    
    workitem.relationships['module'] = {
        'data': {
            'type': 'documents',
            'id': target_document
        }
    }
    
    # Add to document parts
    data_store._add_workitem_to_document(target_document, full_id)
    
    # Build response
    response = {
        "data": {
            "type": "actions",
            "id": "moveToDocument",
            "attributes": {
                "status": "success",
                "message": f"Work item {workitem_id} moved to document {target_document}"
            }
        }
    }
    
    logger.info(f"Moved work item {full_id} to document {target_document}")
    return jsonify(response)


@bp.route('/projects/<project_id>/workitems/<workitem_id>/actions/setParent', methods=['POST'])
@require_auth
def set_parent_workitem(project_id: str, workitem_id: str):
    """Set parent work item through action endpoint."""
    full_id = f"{project_id}/{workitem_id}"
    
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    parent_id = data.get('parentId')
    
    if not parent_id:
        raise ValidationError("parentId is required")
    
    # Update relationship
    if not workitem.relationships:
        workitem.relationships = {}
    
    workitem.relationships['parent'] = {
        'data': {
            'type': 'workitems',
            'id': parent_id
        }
    }
    
    logger.info(f"Set parent {parent_id} for work item: {full_id}")
    return jsonify({
        'data': {
            'type': 'actions',
            'id': 'setParent',
            'attributes': {
                'status': 'success',
                'message': f'Parent work item set to {parent_id}'
            }
        }
    })