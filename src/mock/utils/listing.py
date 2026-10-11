"""
Shared pieces of the read endpoints: the project check, the JSON:API list
response (paging, ``links``, ``meta.totalCount``) and project-scoped links.
"""

from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

from flask import jsonify, request

from ..middleware.error_handler import NotFoundError
from ..storage.data_store import data_store
from .parts import (
    REST_PREFIX,
    base_url_of,
    paginate,
    pagination_links,
    parse_fields,
    parse_pagination,
)


def require_project(project_id: str) -> None:
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)


def require_workitem(project_id: str, workitem_id: str) -> str:
    """The full id ``P/WI`` of an existing work item, else 404."""
    require_project(project_id)
    full_id = f"{project_id}/{workitem_id}"
    if full_id not in data_store.workitems:
        raise NotFoundError("workitems", full_id)
    return full_id


def project_url(project_id: str, *segments: str) -> str:
    """``<base>/polarion/rest/v1/projects/<p>/<seg>/...``, segments encoded."""
    path = "/".join(quote(str(s), safe="") for s in (project_id, *segments))
    return f"{base_url_of(request)}{REST_PREFIX}/projects/{path}"


def fields_of(kind: str) -> Optional[List[str]]:
    """The sparse fieldset requested for ``kind`` (``None`` = all)."""
    return parse_fields(request.args.get(f"fields[{kind}]"))


def list_response(items: List[Any], render: Callable[[Any], Dict[str, Any]]):
    """One page of ``items`` as a JSON:API list with Polarion's links."""
    page_size, page_number = parse_pagination(request.args)
    return jsonify(
        {
            "links": pagination_links(request, page_number, page_size, len(items)),
            "data": [render(item) for item in paginate(items, page_size, page_number)],
            "meta": {"totalCount": len(items)},
        }
    )


def single_response(resource: Dict[str, Any]):
    self_link = resource["links"]["self"]
    return jsonify({"data": resource, "links": {"self": self_link}})
