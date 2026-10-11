"""
Collections (Polarion REST v1, read only).

``GET /projects/{p}/collections``                 list (paged, ``query``)
``GET /projects/{p}/collections/{collectionId}``  one collection

Data: the seeded demo collections and, per dumped project, a collection of
its documents (``storage/demo_seed.py``).
"""

from typing import Any, Dict

from flask import Blueprint, request

from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError
from ..storage.data_store import data_store
from ..storage.demo_seed import DEMO_AUTHOR
from ..utils import lucene
from ..utils.listing import fields_of, list_response, project_url
from ..utils.listing import require_project, single_response
from ..utils.parts import apply_fields

bp = Blueprint("collections", __name__)


def _timestamp(value) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _attributes(collection) -> Dict[str, Any]:
    attrs = collection.attributes
    attributes: Dict[str, Any] = {
        "id": attrs.id,
        "name": attrs.name,
        "created": _timestamp(attrs.created),
        "updated": _timestamp(attrs.updated),
    }
    if attrs.description:
        attributes["description"] = {
            "type": attrs.description.type,
            "value": attrs.description.value,
        }
    if attrs.closedOn:
        attributes["closedOn"] = _timestamp(attrs.closedOn)
    return attributes


def _render(collection) -> Dict[str, Any]:
    project_id = collection.id.split("/", 1)[0]
    documents = ((collection.relationships or {}).get("documents") or {}).get(
        "data"
    ) or []
    return {
        "type": "collections",
        "id": collection.id,
        "attributes": apply_fields(_attributes(collection), fields_of("collections")),
        "relationships": {
            "author": {"data": {"type": "users", "id": DEMO_AUTHOR}},
            "project": {"data": {"type": "projects", "id": project_id}},
            "documents": {"data": documents, "meta": {"totalCount": len(documents)}},
        },
        "links": {
            "self": project_url(project_id, "collections", collection.attributes.id)
        },
    }


@bp.route("/projects/<project_id>/collections", methods=["GET"])
@require_auth
def list_collections(project_id: str):
    require_project(project_id)
    query = request.args.get("query")
    collections = [
        c
        for c in data_store.collections.values()
        if c.id.startswith(f"{project_id}/") and lucene.matches(_attributes(c), query)
    ]
    return list_response(collections, _render)


@bp.route("/projects/<project_id>/collections/<collection_id>", methods=["GET"])
@require_auth
def get_collection(project_id: str, collection_id: str):
    require_project(project_id)
    collection = data_store.collections.get(f"{project_id}/{collection_id}")
    if collection is None:
        raise NotFoundError("collections", f"{project_id}/{collection_id}")
    return single_response(_render(collection))
