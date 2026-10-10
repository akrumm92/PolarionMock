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
from ..utils.parts import (
    absolutize_links, apply_fields, base_url_of, paginate, pagination_links, parse_fields,
    parse_pagination,
)

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('workitems', __name__)

# Initialize response builder
response_builder = JSONAPIResponseBuilder()


def _with_backlinks(resource: Dict[str, Any], fields) -> Dict[str, Any]:
    """Add the ``backlinkedWorkItems`` relationship (links stored on other
    work items that point here) when the fieldset asks for it."""
    if fields is not None and 'backlinkedWorkItems' not in fields:
        return resource
    backlinks = data_store.backlinks_of(resource['id'])
    resource.setdefault('relationships', {})
    resource['relationships'] = {
        **resource['relationships'],
        'backlinkedWorkItems': {
            'data': [{'type': 'linkedworkitems', 'id': link['id']} for link in backlinks],
            'meta': {'totalCount': len(backlinks)},
        },
    }
    return resource


def _link_resource(link: Dict[str, Any], project_id: str, workitem_id: str, base_url: str) -> Dict[str, Any]:
    """A stored link as JSON:API resource with its absolute self link."""
    role = link.get('attributes', {}).get('role')
    target = link.get('relationships', {}).get('workItem', {}).get('data', {}).get('id', '')
    return {
        **link,
        'links': {'self': f"{base_url}/polarion/rest/v1/projects/{project_id}/workitems/"
                          f"{workitem_id}/linkedworkitems/{role}/{target}"},
    }


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
    
    # Convert to JSON:API format (sparse fieldsets + absolute links)
    base_url = base_url_of(request)
    fields = parse_fields(request.args.get('fields[workitems]'))
    resources = []
    for wi in workitems_page:
        resource = _with_backlinks(absolutize_links(wi.to_json_api(), base_url), fields)
        if 'attributes' in resource:
            resource['attributes'] = apply_fields(resource['attributes'], fields)
        resources.append(resource)
    
    # Handle includes
    included = []
    if 'module' in include:
        for wi in workitems_page:
            if wi.relationships and 'module' in wi.relationships:
                module_id = wi.relationships['module']['data']['id']
                if module_id in data_store.documents:
                    included.append(absolutize_links(data_store.document_resource(data_store.documents[module_id]), base_url))
    
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
        **({'next': build_page_url(page_number + 1)} if has_next else {}),
        **({'prev': build_page_url(page_number - 1)} if has_prev else {}),
        'portal': f"https://polarion.example.com/polarion/#/project/{project_id}/workitems"
    }
    
    # Build response
    response = {
        'links': links,
        'data': resources
    }
    
    if included:
        response['included'] = included
    
    response['meta'] = {'totalCount': total_count}
    
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
    
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)

    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)

    base_url = base_url_of(request)
    resource = absolutize_links(workitem.to_json_api(), base_url)

    # Sparse fieldsets: fields[workitems]=id,title,type,... (@all/@basic = everything)
    fields = parse_fields(request.args.get('fields[workitems]'))
    resource = _with_backlinks(resource, fields)
    if 'attributes' in resource:
        resource['attributes'] = apply_fields(resource['attributes'], fields)
        if not resource['attributes']:
            del resource['attributes']

    # include=module embeds the document the work item lives in
    included = []
    include = [item.strip() for item in request.args.get('include', '').split(',') if item.strip()]
    if 'module' in include and workitem.relationships and 'module' in workitem.relationships:
        module_id = workitem.relationships['module'].get('data', {}).get('id')
        document = data_store.documents.get(module_id)
        if document is not None:
            included.append(absolutize_links(data_store.document_resource(document), base_url))

    # Build response (top-level self link like production)
    response = response_builder.build_response(
        data=resource,
        included=included or None,
        links={"self": request.url},
    )

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


@bp.route('/projects/<project_id>/workitems', methods=['DELETE'])
@require_auth
def delete_workitems(project_id: str):
    """Delete a list of work items (Polarion REST v1: the only work item delete).

    Body: ``{"data": [{"type": "workitems", "id": "PROJ/PROJ-1"}, ...]}``.
    Every id is checked before anything is deleted; a deleted work item also
    leaves every document it was part of.
    """
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('data'), list) or not data['data']:
        raise ValidationError("Request must contain a non-empty 'data' array")
    full_ids = []
    for item in data['data']:
        if not isinstance(item, dict) or item.get('type') != 'workitems':
            raise ValidationError("Resource type must be 'workitems'")
        full_id = str(item.get('id') or '')
        if not full_id.startswith(f"{project_id}/"):
            raise ValidationError(f"Work item id '{full_id}' is not an id of project {project_id}")
        if full_id not in data_store.workitems:
            raise NotFoundError("workitems", full_id)
        full_ids.append(full_id)
    for full_id in full_ids:
        data_store.delete_workitem(full_id)
    logger.info(f"Deleted work items: {', '.join(full_ids)}")
    return '', 204


@bp.route('/projects/<project_id>/workitems/<workitem_id>', methods=['DELETE'])
@require_auth
def delete_workitem(project_id: str, workitem_id: str):
    """Delete one work item.

    Not part of Polarion REST v1 (it deletes through the list endpoint
    above); kept because this repository's client
    (``src/polarion_api/work_items.py`` ``delete_work_item``) and its tests
    clean up with it.
    """
    full_id = f"{project_id}/{workitem_id}"
    
    if full_id not in data_store.workitems:
        raise NotFoundError("workitems", full_id)
    
    data_store.delete_workitem(full_id)
    
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
    
    links = getattr(workitem, 'linkedWorkItems', None) or []
    page_size, page_number = parse_pagination(request.args)
    base_url = base_url_of(request)
    fields = parse_fields(request.args.get('fields[linkedworkitems]'))
    data = []
    for link in paginate(links, page_size, page_number):
        resource = _link_resource(link, project_id, workitem_id, base_url)
        resource['attributes'] = apply_fields(resource.get('attributes', {}), fields)
        data.append(resource)
    return jsonify({
        'links': pagination_links(request, page_number, page_size, len(links)),
        'data': data,
        'meta': {'totalCount': len(links)},
    })


def _relationship_data(workitem, relationship_id: str):
    """``(data, is_list)`` of one work item relationship, or None if the mock
    holds no such relationship. Links come from the one link store: the links
    stored on the item (``linkedWorkItems``) and those pointing to it
    (``backlinkedWorkItems``)."""
    if relationship_id == 'linkedWorkItems':
        links = getattr(workitem, 'linkedWorkItems', None) or []
        return [{'type': 'linkedworkitems', 'id': link['id']} for link in links], True
    if relationship_id == 'backlinkedWorkItems':
        links = data_store.backlinks_of(workitem.id)
        return [{'type': 'linkedworkitems', 'id': link['id']} for link in links], True
    relationship = (workitem.relationships or {}).get(relationship_id)
    if relationship is None or 'data' not in relationship:
        return None
    data = relationship['data']
    if isinstance(data, list):
        return [{'type': item.get('type'), 'id': item.get('id')} for item in data], True
    return data, False


@bp.route(
    '/projects/<project_id>/workitems/<workitem_id>/relationships/<relationship_id>',
    methods=['GET'],
)
@require_auth
def get_workitem_relationship(project_id: str, workitem_id: str, relationship_id: str):
    """One relationship of a work item (``getWorkItemsRelationships``).

    A to-many relationship is paged (``page[size]``/``page[number]``) and
    carries ``meta.totalCount``; a to-one relationship answers a single
    identifier.
    """
    full_id = f"{project_id}/{workitem_id}"
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)

    found = _relationship_data(workitem, relationship_id)
    if found is None:
        raise NotFoundError("relationships", relationship_id)
    data, is_list = found
    if not is_list:
        return jsonify({'data': data, 'links': {'self': request.url}})

    page_size, page_number = parse_pagination(request.args)
    return jsonify({
        'links': pagination_links(request, page_number, page_size, len(data)),
        'data': paginate(data, page_size, page_number),
        'meta': {'totalCount': len(data)},
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
                             if l.get('attributes', {}).get('role') == role and
                             l.get('relationships', {}).get('workItem', {}).get('data', {}).get('id') == target_id),
                             None)
        
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

        # A parent link also drives the outline numbering in the Document Parts API
        if role == 'parent':
            workitem._parent_workitem_id = target_id
            if not workitem.relationships:
                workitem.relationships = {}
            workitem.relationships['parent'] = {
                'data': {'type': 'workitems', 'id': target_id}
            }
        
        logger.info(f"Created link: {full_id} --[{role}]--> {target_id}")
    
    base_url = base_url_of(request)
    return jsonify({'data': [
        {'type': link['type'], 'id': link['id'],
         'links': _link_resource(link, project_id, workitem_id, base_url)['links']}
        for link in created_links
    ]}), 201


@bp.route('/projects/<project_id>/workitems/<workitem_id>/linkedworkitems', methods=['DELETE'])
@require_auth
def delete_linked_workitems(project_id: str, workitem_id: str):
    """Delete a list of links stored on this work item.

    Body: ``{"data": [{"type": "linkedworkitems", "id": "P/WI/role/P/TARGET"}]}``.
    Every id is checked before anything is deleted.
    """
    full_id = f"{project_id}/{workitem_id}"
    workitem = data_store.workitems.get(full_id)
    if not workitem:
        raise NotFoundError("workitems", full_id)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('data'), list) or not data['data']:
        raise ValidationError("Request must contain a non-empty 'data' array")
    stored = {link['id'] for link in getattr(workitem, 'linkedWorkItems', None) or []}
    doomed = set()
    for item in data['data']:
        if not isinstance(item, dict) or item.get('type') != 'linkedworkitems':
            raise ValidationError("Resource type must be 'linkedworkitems'")
        if item.get('id') not in stored:
            raise NotFoundError("linkedworkitems", str(item.get('id')))
        doomed.add(item['id'])
    workitem.linkedWorkItems = [l for l in workitem.linkedWorkItems if l['id'] not in doomed]
    for link_id in doomed:
        if link_id.split('/')[2] == 'parent':
            workitem._parent_workitem_id = None
            (workitem.relationships or {}).pop('parent', None)
    logger.info(f"Deleted links of {full_id}: {', '.join(sorted(doomed))}")
    return '', 204


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