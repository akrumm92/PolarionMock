"""
Document Parts API endpoints for Polarion Mock Server.

``GET  /projects/{p}/spaces/{s}/documents/{d}/parts``
    Paginated, ordered list of the document's parts (headings, work items,
    text blocks, page breaks ...) with ``meta.totalCount`` and JSON:API
    pagination links - exactly what a read-only document export needs.

``POST /projects/{p}/spaces/{s}/documents/{d}/parts``
    Step 2 of Polarion's two-step process that makes a work item visible in
    a document (step 1 creates the work item with a ``module`` relationship,
    which leaves it in the Recycle Bin).
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from ..storage.data_store import data_store
from ..utils.response_builder import JSONAPIResponseBuilder
from ..utils.parts import (
    absolutize_links,
    base_url_of,
    document_parts_url,
    paginate,
    pagination_links,
    parse_fields,
    parse_pagination,
    render_part,
    apply_fields,
)
from ..middleware.auth import require_auth
from ..middleware.error_handler import APIError, NotFoundError, ValidationError, ConflictError
from ..storage.document_body import unnamed_blocks

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('document_parts', __name__)

# Initialize response builder
response_builder = JSONAPIResponseBuilder()


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
    """Calculate the 1-based position for a new document part.

    Args:
        previous_part_id: ID (short or full) of the part to insert after
        document_id: Document ID
    """
    parts = data_store.document_parts.setdefault(document_id, [])
    if not previous_part_id:
        return len(parts) + 1
    index = data_store.find_part(document_id, previous_part_id)
    if index is None:
        # Previous part not found, add to end
        return len(parts) + 1
    return index + 2  # Insert after this position


def _document_or_404(project_id: str, space_id: str, document_name: str) -> str:
    """Return the full document id or raise the matching 404."""
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    document_id = f"{project_id}/{space_id}/{document_name}"
    if document_id not in data_store.documents:
        raise NotFoundError("documents", document_id)
    return document_id


def _included_workitems(parts: List[Dict[str, Any]], base_url: str) -> List[Dict[str, Any]]:
    """Work items referenced by ``parts`` for ``include=workItem``."""
    fields = parse_fields(request.args.get('fields[workitems]'))
    included: List[Dict[str, Any]] = []
    seen = set()
    for part in parts:
        workitem_id = part.get("workitem_id")
        if not workitem_id or workitem_id in seen:
            continue
        workitem = data_store.workitems.get(workitem_id)
        if workitem is None:
            continue
        seen.add(workitem_id)
        resource = workitem.to_json_api()
        if "attributes" in resource:
            resource["attributes"] = apply_fields(resource["attributes"], fields)
        included.append(absolutize_links(resource, base_url))
    return included


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_name>/parts', methods=['GET'])
@require_auth
def get_document_parts(project_id: str, space_id: str, document_name: str):
    """Get all document parts in document order (paginated).

    Query parameters (as in Polarion REST API v1):
    - ``page[size]`` (default 100, max 100), ``page[number]`` (1-based)
    - ``fields[document_parts]`` sparse fieldsets (``@all`` or a list)
    - ``include=workItem`` to embed the referenced work items

    Work items in the "Recycle Bin" are NOT included.
    """
    document_id = _document_or_404(project_id, space_id, document_name)
    base_url = base_url_of(request)

    parts = data_store.get_parts(document_id)
    unnamed = unnamed_blocks(parts)
    if unnamed:
        # Polarion cannot list the parts of a text holding a block without an id
        position, content = unnamed[0]
        raise APIError(
            f"Document {document_id}: block {position} of the document text has no id, "
            f"so it is no document part: {content[:120]}",
            status_code=500,
        )
    total_count = len(parts)
    page_size, page_number = parse_pagination(request.args)
    page_parts = paginate(parts, page_size, page_number)

    fields = parse_fields(request.args.get('fields[document_parts]'))
    data = [render_part(document_id, part, base_url, fields) for part in page_parts]

    response: Dict[str, Any] = {
        "links": pagination_links(request, page_number, page_size, total_count),
        "data": data,
    }

    include = [item.strip() for item in request.args.get('include', '').split(',') if item.strip()]
    if 'workItem' in include:
        included = _included_workitems(page_parts, base_url)
        if included:
            response["included"] = included

    response["meta"] = {"totalCount": total_count}

    logger.info(
        "Retrieved %d/%d parts for document %s (page %d, size %d)",
        len(data), total_count, document_id, page_number, page_size,
    )
    return jsonify(response)


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_name>/parts/<part_id>', methods=['GET'])
@require_auth
def get_document_part(project_id: str, space_id: str, document_name: str, part_id: str):
    """Get a single document part by its short id (e.g. ``heading_VPAT-1``)."""
    document_id = _document_or_404(project_id, space_id, document_name)
    base_url = base_url_of(request)
    for part in data_store.get_parts(document_id):
        if part["id"] == part_id:
            fields = parse_fields(request.args.get('fields[document_parts]'))
            response: Dict[str, Any] = {
                "links": {"self": request.url},
                "data": render_part(document_id, part, base_url, fields),
            }
            if 'workItem' in request.args.get('include', ''):
                included = _included_workitems([part], base_url)
                if included:
                    response["included"] = included
            return jsonify(response)
    raise NotFoundError("document_parts", f"{document_id}/{part_id}")


@bp.route('/projects/<project_id>/spaces/<space_id>/documents/<document_name>/parts', methods=['POST'])
@require_auth
def add_document_part(project_id: str, space_id: str, document_name: str):
    """Add WorkItem to document content (Step 2 of integration).

    This is the CRITICAL second step that makes WorkItems visible in documents.
    Without this, WorkItems remain in the "Recycle Bin" even with module relationship.
    """
    document_id = _document_or_404(project_id, space_id, document_name)
    base_url = base_url_of(request)

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

        if part_type not in ('workitem', 'heading'):
            raise ValidationError(f"Unsupported part type: {part_type}")

        # Get WorkItem reference
        relationships = part_data.get('relationships', {})
        workitem_rel = relationships.get('workItem')
        if not workitem_rel or not workitem_rel.get('data'):
            raise ValidationError("workItem relationship is required")

        workitem_id = workitem_rel['data'].get('id')
        if not workitem_id:
            raise ValidationError("WorkItem ID is required")
        if "/" not in workitem_id:
            workitem_id = f"{project_id}/{workitem_id}"

        # Retrieve WorkItem
        workitem = data_store.workitems.get(workitem_id)
        if not workitem:
            raise NotFoundError("workitems", workitem_id)

        # Verify module relationship matches document. A work item without a
        # module (created in the tracker) is moved into this document.
        if workitem.relationships and 'module' in workitem.relationships:
            module_data = workitem.relationships['module'].get('data', {})
            if module_data.get('id') != document_id:
                raise ValidationError(f"WorkItem module ({module_data.get('id')}) does not match document ({document_id})")
        else:
            if not workitem.relationships:
                workitem.relationships = {}
            workitem.relationships['module'] = {
                'data': {'type': 'documents', 'id': document_id}
            }

        if getattr(workitem, '_is_in_document', False) and \
                data_store.find_part(document_id, f"{part_type}_{workitem_id.split('/', 1)[-1]}") is not None:
            raise ConflictError(f"WorkItem {workitem_id} is already part of document {document_id}")

        # Calculate position
        previous_part_id = None
        if 'previousPart' in relationships:
            previous_part_id = (relationships['previousPart'].get('data') or {}).get('id')

        position = calculate_position(previous_part_id, document_id)
        short_id = workitem_id.split('/', 1)[-1]
        if part_type == "heading":
            content = f'<h2 id="polarion_wiki macro name=module-workitem;params=id={short_id}"></h2>'
        else:
            content = f'<div id="polarion_wiki macro name=module-workitem;params=id={short_id}"></div>'

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
            header_id = previous_part_id.rsplit("heading_", 1)[-1]
            if "/" not in header_id and project_id:
                header_id = f"{project_id}/{header_id}"

            header_wi = data_store.workitems.get(header_id)
            if header_wi and hasattr(header_wi.attributes, 'outlineNumber') and header_wi.attributes.outlineNumber:
                parent_outline = header_wi.attributes.outlineNumber
                # Generate child outline (e.g., 4.1-1 for first item under 4.1)
                existing_children = sum(1 for wi in data_store.workitems.values()
                                      if hasattr(wi.attributes, 'outlineNumber') and
                                      wi.attributes.outlineNumber and
                                      wi.attributes.outlineNumber.startswith(f"{parent_outline}-"))
                outline_number = f"{parent_outline}-{existing_children + 1}"

        workitem.attributes.outlineNumber = outline_number

        # Store document part (canonical shape)
        part = data_store.add_part(
            document_id,
            part_id=f"{part_type}_{short_id}",
            part_type=part_type,
            content=content,
            workitem_id=workitem_id,
            position=position,
        )
        # Polarion answers a POST with type/id/links only (no attributes)
        created_parts.append(render_part(document_id, part, base_url, with_attributes=False))

        logger.info(f"Added WorkItem {workitem_id} to document {document_id} at position {position} with outline {outline_number}")

    # Build response
    response = {
        "data": created_parts
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
