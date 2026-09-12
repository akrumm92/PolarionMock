"""
Mock-only administration endpoints (NOT part of the Polarion REST API).

They live under ``/mock/admin`` so they never collide with Polarion paths:

``GET  /mock/admin/dumps``      list the Polarion dumps that are loaded
``POST /mock/admin/dumps``      load a dump (body = polarion_document_raw.json)
``POST /mock/admin/reset``      reseed the store (dummy data + dumps on disk)
``GET  /mock/admin/documents``  every document with its coordinates and counts

Authentication applies like everywhere else.
"""

import logging
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from ..middleware.auth import require_auth
from ..middleware.error_handler import ValidationError
from ..storage.data_store import data_store
from ..storage.dump_loader import DumpFormatError, dump_directories
from ..utils.parts import base_url_of, document_parts_url, split_document_id

logger = logging.getLogger(__name__)

bp = Blueprint('mock_admin', __name__)


def _document_overview(base_url: str) -> List[Dict[str, Any]]:
    overview: List[Dict[str, Any]] = []
    for document_id, document in sorted(data_store.documents.items()):
        project_id, space_id, document_name = split_document_id(document_id)
        parts = data_store.get_parts(document_id)
        workitem_ids = {p["workitem_id"] for p in parts if p.get("workitem_id")}
        overview.append({
            "id": document_id,
            "project": project_id,
            "space": space_id,
            "document": document_name,
            "title": document.attributes.title,
            "parts": len(parts),
            "workitems": len(workitem_ids),
            "parts_url": document_parts_url(base_url, document_id),
        })
    return overview


@bp.route('/mock/admin/dumps', methods=['GET'])
@require_auth
def list_dumps():
    """List loaded dumps and the directories that are scanned."""
    return jsonify({
        "dump_directories": [str(path) for path in dump_directories()],
        "dumps": data_store.dump_summaries,
    })


@bp.route('/mock/admin/dumps', methods=['POST'])
@require_auth
def load_dump():
    """Load a raw Polarion document dump sent in the request body."""
    if not request.is_json:
        raise ValidationError("Request must be JSON (a polarion_document_raw.json dump)")
    dump = request.get_json(silent=True)
    try:
        summary = data_store.load_dump(dump, source=f"POST {request.path}")
    except DumpFormatError as error:
        raise ValidationError(f"Not a Polarion dump: {error}")
    logger.info("Loaded dump via API: %s", summary["document_id"])
    return jsonify({"data": summary}), 201


@bp.route('/mock/admin/reset', methods=['POST'])
@require_auth
def reset_store():
    """Reseed the in-memory store (dummy data + dumps from disk)."""
    data_store.reset()
    return jsonify({
        "status": "reset",
        "projects": len(data_store.projects.get_all()),
        "documents": len(data_store.documents),
        "workitems": len(data_store.workitems),
        "dumps": data_store.dump_summaries,
    })


@bp.route('/mock/admin/documents', methods=['GET'])
@require_auth
def list_documents():
    """Every document the mock serves, with coordinates for a workflow overlay."""
    return jsonify({"data": _document_overview(base_url_of(request))})
