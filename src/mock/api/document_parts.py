"""
Document Parts API endpoints for Polarion Mock Server.

Implements the critical Document Parts API that makes WorkItems visible in documents.
This is Step 2 of the mandatory two-step process.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.document_part import DocumentPart, RecycleBin
from ..storage.data_store import data_store
from ..utils.response_builder import JSONAPIResponseBuilder
from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError, ValidationError, ConflictError

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('document_parts', __name__)

# Initialize response builder and recycle bin
response_builder = JSONAPIResponseBuilder()
recycle_bin = RecycleBin()


def generate_outline_number(position: int, workitem_type: str, 
                           parent_outline: Optional[str] = None) -> str:
    """Generate outline number based on document position and hierarchy.
    
    Args:
        position: Position in document
        workitem_type: Type of work item (heading, requirement, etc.)
        parent_outline: Parent's outline number if nested
    
    Returns:
        Generated outline number (e.g., "FC-4.1-1" for item under section 4.1)
    """
    if parent_outline:
        # Child of another WorkItem - append position to parent outline
        if "-" in parent_outline:
            # Already has suffix, add another level
            return f"{parent_outline}.{position}"
        else:
            # First child level
            return f"{parent_outline}-{position}"
    elif workitem_type == "heading":
        # Top-level heading - calculate section number
        major = (position - 1) // 10 + 1
        minor = (position - 1) % 10 + 1
        return f"{major}.{minor}"
    else:
        # Regular WorkItem in document
        # Format: FC-section-position (e.g., "FC-4.1-1")
        section = ((position - 1) // 100) + 1
        subsection = ((position - 1) % 100) // 10 + 1
        item_num = (position - 1) % 10 + 1
        return f"FC-{section}.{subsection}-{item_num}"


def calculate_position(previous_part_id: Optional[str], document_id: str) -> int:
    """Calculate position for new document part.
    
    Args:
        previous_part_id: ID of part to insert after
        document_id: Document ID
    
    Returns:
        Calculated position number
    """
    if document_id not in data_store.document_parts:
        data_store.document_parts[document_id] = []
    
    parts = data_store.document_parts[document_id]
    
    if not previous_part_id:
        # Add to end
        return len(parts) + 1
    
    # Find position after previous part
    for i, part in enumerate(parts):
        if part.get('id') == previous_part_id:
            return i + 2  # Insert after this position
    
    # Previous part not found, add to end
    return len(parts) + 1


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_name>/parts', methods=['GET'])
@require_auth
def get_document_parts(project_id: str, space_id: str, document_name: str):
    """Get all document parts in order.
    
    Returns parts that have been added via the Document Parts API.
    WorkItems in "Recycle Bin" are NOT included.
    """
    document_id = f"{project_id}/{space_id}/{document_name}"
    
    # Check if document exists
    if document_id not in data_store.documents:
        raise NotFoundError("documents", document_id)
    
    # Get document parts
    parts = data_store.document_parts.get(document_id, [])
    
    # Build response with only parts that are in document
    response_parts = []
    for part in parts:
        # Check if it's a WorkItem part
        if part.get('type') == 'document_parts':
            workitem_id = part.get('workitem_id')
            if workitem_id:
                # Verify WorkItem is marked as in document
                workitem = data_store.workitems.get(workitem_id)
                if workitem and hasattr(workitem, '_is_in_document') and workitem._is_in_document:
                    response_parts.append(part)
            else:
                # Non-workitem part (e.g., text block)
                response_parts.append(part)
    
    response = {
        "links": {
            "self": request.url
        },
        "data": response_parts
    }
    
    logger.info(f"Retrieved {len(response_parts)} parts for document {document_id}")
    return jsonify(response)


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_name>/parts', methods=['POST'])
@require_auth
def add_document_part(project_id: str, space_id: str, document_name: str):
    """Add WorkItem to document content (Step 2 of integration).
    
    This is the CRITICAL second step that makes WorkItems visible in documents.
    Without this, WorkItems remain in the "Recycle Bin" even with module relationship.
    """
    document_id = f"{project_id}/{space_id}/{document_name}"
    
    # Check if document exists
    if document_id not in data_store.documents:
        raise NotFoundError("documents", document_id)
    
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
        part_type = attributes.get('type', 'workitem')
        
        if part_type != 'workitem':
            raise ValidationError(f"Unsupported part type: {part_type}")
        
        # Get WorkItem reference
        relationships = part_data.get('relationships', {})
        workitem_rel = relationships.get('workItem')
        if not workitem_rel or not workitem_rel.get('data'):
            raise ValidationError("workItem relationship is required")
        
        workitem_id = workitem_rel['data'].get('id')
        if not workitem_id:
            raise ValidationError("WorkItem ID is required")
        
        # Retrieve WorkItem
        workitem = data_store.workitems.get(workitem_id)
        if not workitem:
            raise NotFoundError("workitems", workitem_id)
        
        # Verify module relationship matches document
        if workitem.relationships and 'module' in workitem.relationships:
            module_data = workitem.relationships['module'].get('data', {})
            if module_data.get('id') != document_id:
                raise ValidationError(f"WorkItem module ({module_data.get('id')}) does not match document ({document_id})")
        else:
            raise ValidationError(f"WorkItem {workitem_id} has no module relationship")
        
        # Calculate position
        previous_part_id = None
        if 'previousPart' in relationships:
            previous_part_id = relationships['previousPart']['data'].get('id')
        
        position = calculate_position(previous_part_id, document_id)
        
        # Create document part
        document_part = DocumentPart.create_workitem_part(
            document_id=document_id,
            workitem_id=workitem_id,
            position=position,
            previous_part_id=previous_part_id
        )
        
        # Update WorkItem state - CRITICAL for visibility
        workitem._is_in_document = True
        workitem._in_recycle_bin = False
        workitem._document_position = position
        
        # Generate and assign outline number
        parent_outline = None
        if hasattr(workitem, '_parent_workitem_id') and workitem._parent_workitem_id:
            parent_wi = data_store.workitems.get(workitem._parent_workitem_id)
            if parent_wi and hasattr(parent_wi.attributes, 'outlineNumber'):
                parent_outline = parent_wi.attributes.outlineNumber
        
        outline_number = generate_outline_number(
            position, 
            workitem.attributes.type if hasattr(workitem.attributes, 'type') else 'requirement',
            parent_outline
        )
        
        # Special handling for items positioned after specific headers
        # If positioned after a header like PYTH-9397 (4.1), generate child outline
        if previous_part_id and "heading_" in previous_part_id:
            # Extract header workitem ID
            header_id = previous_part_id.replace("heading_", "")
            if "/" not in header_id and project_id:
                header_id = f"{project_id}/{header_id}"
            
            header_wi = data_store.workitems.get(header_id)
            if header_wi and hasattr(header_wi.attributes, 'outlineNumber'):
                parent_outline = header_wi.attributes.outlineNumber
                # Generate child outline (e.g., 4.1-1 for first item under 4.1)
                existing_children = sum(1 for wi in data_store.workitems.values()
                                      if hasattr(wi.attributes, 'outlineNumber') and 
                                      wi.attributes.outlineNumber and
                                      wi.attributes.outlineNumber.startswith(f"{parent_outline}-"))
                outline_number = f"{parent_outline}-{existing_children + 1}"
        
        workitem.attributes.outlineNumber = outline_number
        
        # Remove from recycle bin if present
        recycle_bin.remove(workitem_id)
        
        # Store document part
        if document_id not in data_store.document_parts:
            data_store.document_parts[document_id] = []
        
        data_store.document_parts[document_id].append(document_part.to_json_api())
        created_parts.append(document_part.to_json_api())
        
        logger.info(f"✅ Added WorkItem {workitem_id} to document {document_id} at position {position} with outline {outline_number}")
    
    # Build response
    response = {
        "data": created_parts
    }
    
    return jsonify(response), 201


@bp.route('/projects/<project_id>/workitems/<workitem_id>/linkedworkitems', methods=['POST'])
@require_auth
def create_linked_workitem(project_id: str, workitem_id: str):
    """Create parent-child relationship between WorkItems.
    
    Note: This does NOT affect document visibility - WorkItems still need
    to be added via Document Parts API to be visible.
    """
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
        raise ValidationError("Request must contain 'data' array")
    
    if not isinstance(data['data'], list):
        raise ValidationError("'data' must be an array")
    
    created_links = []
    
    for link_data in data['data']:
        if link_data.get('type') != 'linkedworkitems':
            raise ValidationError("Resource type must be 'linkedworkitems'")
        
        attributes = link_data.get('attributes', {})
        role = attributes.get('role', 'parent')
        
        relationships = link_data.get('relationships', {})
        linked_workitem = relationships.get('workItem')
        if not linked_workitem or not linked_workitem.get('data'):
            raise ValidationError("workItem relationship is required")
        
        parent_id = linked_workitem['data'].get('id')
        if not parent_id:
            raise ValidationError("Parent WorkItem ID is required")
        
        # Check if parent exists
        if parent_id not in data_store.workitems:
            raise NotFoundError("workitems", parent_id)
        
        # Create relationship
        if role == 'parent':
            # Set parent for child workitem
            workitem._parent_workitem_id = parent_id
            
            # Update relationships
            if not workitem.relationships:
                workitem.relationships = {}
            
            workitem.relationships['parent'] = {
                'data': {
                    'type': 'workitems',
                    'id': parent_id
                }
            }
            
            link_id = f"{full_id}/parent/{parent_id}"
        else:
            # Other relationship types
            link_id = f"{full_id}/{role}/{parent_id}"
        
        created_links.append({
            "type": "linkedworkitems",
            "id": link_id
        })
        
        logger.info(f"Created {role} relationship: {full_id} -> {parent_id}")
    
    # Build response
    response = {
        "data": created_links
    }
    
    return jsonify(response), 201


# Debug endpoints (Mock only)
@bp.route('/mock/debug/recycle-bin/<path:document_id>', methods=['GET'])
@require_auth
def get_recycle_bin_items(document_id: str):
    """List all WorkItems in document's Recycle Bin (mock debug endpoint)."""
    items = []
    
    for workitem in data_store.workitems.values():
        if hasattr(workitem, '_in_recycle_bin') and workitem._in_recycle_bin:
            if workitem.relationships and 'module' in workitem.relationships:
                module_id = workitem.relationships['module']['data']['id']
                if module_id == document_id:
                    items.append({
                        "id": workitem.id,
                        "title": workitem.attributes.title if hasattr(workitem.attributes, 'title') else "",
                        "type": workitem.attributes.type if hasattr(workitem.attributes, 'type') else "",
                        "in_recycle_bin": True,
                        "has_module": True,
                        "is_in_document": getattr(workitem, '_is_in_document', False)
                    })
    
    response = {
        "document_id": document_id,
        "recycle_bin_count": len(items),
        "items": items
    }
    
    return jsonify(response)


@bp.route('/mock/debug/workitem-states/<path:workitem_id>', methods=['GET'])
@require_auth
def get_workitem_state(workitem_id: str):
    """Show internal state of a WorkItem (mock debug endpoint)."""
    workitem = data_store.workitems.get(workitem_id)
    
    if not workitem:
        raise NotFoundError("workitems", workitem_id)
    
    response = {
        "id": workitem.id,
        "title": workitem.attributes.title if hasattr(workitem.attributes, 'title') else "",
        "type": workitem.attributes.type if hasattr(workitem.attributes, 'type') else "",
        "in_document": getattr(workitem, '_is_in_document', False),
        "outline_number": workitem.attributes.outlineNumber if hasattr(workitem.attributes, 'outlineNumber') else None,
        "document_position": getattr(workitem, '_document_position', None),
        "in_recycle_bin": getattr(workitem, '_in_recycle_bin', False),
        "parent_workitem_id": getattr(workitem, '_parent_workitem_id', None),
        "has_module": bool(workitem.relationships and 'module' in workitem.relationships),
        "module_id": workitem.relationships['module']['data']['id'] if workitem.relationships and 'module' in workitem.relationships else None
    }
    
    return jsonify(response)