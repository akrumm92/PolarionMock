"""
Work item comments (Polarion REST v1).

``GET  /projects/{p}/workitems/{wi}/comments``              list (paged)
``POST /projects/{p}/workitems/{wi}/comments``              create a list;
    a reply names its ``parentComment`` (``P/WI/<commentId>``)
``GET  /projects/{p}/workitems/{wi}/comments/{commentId}``  one comment
``PATCH /projects/{p}/workitems/{wi}/comments/{commentId}`` set ``resolved``

A comment's id is ``P/WI/<commentId>``; ``commentId`` counts up per work item.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from flask import Blueprint, g, jsonify, request

from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError, ValidationError
from ..storage.data_store import data_store
from ..utils.parts import (
    REST_PREFIX,
    apply_fields,
    base_url_of,
    paginate,
    pagination_links,
    parse_fields,
    parse_pagination,
)

logger = logging.getLogger(__name__)

bp = Blueprint("comments", __name__)

KIND = "workitem_comments"


def _workitem_or_404(project_id: str, workitem_id: str) -> str:
    if not data_store.projects.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    full_id = f"{project_id}/{workitem_id}"
    if full_id not in data_store.workitems:
        raise NotFoundError("workitems", full_id)
    return full_id


def _comment_or_404(full_id: str, comment_id: str) -> Dict[str, Any]:
    for comment in data_store.comments.get(full_id, []):
        if comment["id"] == comment_id:
            return comment
    raise NotFoundError(KIND, f"{full_id}/{comment_id}")


def _render(
    full_id: str,
    comment: Dict[str, Any],
    base_url: str,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    project_id, workitem_id = full_id.split("/", 1)
    attributes = {
        "created": comment["created"],
        "id": comment["id"],
        "resolved": comment["resolved"],
        "text": comment["text"],
    }
    if comment.get("title") is not None:
        attributes["title"] = comment["title"]
    children = [
        c["id"]
        for c in data_store.comments.get(full_id, [])
        if c.get("parent") == comment["id"]
    ]
    relationships: Dict[str, Any] = {
        "author": {"data": {"type": "users", "id": comment["author"]}},
        "childComments": {
            "data": [{"type": KIND, "id": f"{full_id}/{c}"} for c in children],
            "meta": {"totalCount": len(children)},
        },
    }
    if comment.get("parent"):
        relationships["parentComment"] = {
            "data": {"type": KIND, "id": f"{full_id}/{comment['parent']}"}
        }
    return {
        "type": KIND,
        "id": f"{full_id}/{comment['id']}",
        "attributes": apply_fields(attributes, fields),
        "relationships": relationships,
        "links": {
            "self": f"{base_url}{REST_PREFIX}/projects/{quote(project_id, safe='')}"
            f"/workitems/{quote(workitem_id, safe='')}/comments/{comment['id']}"
        },
    }


@bp.route("/projects/<project_id>/workitems/<workitem_id>/comments", methods=["GET"])
@require_auth
def list_comments(project_id: str, workitem_id: str):
    """The work item's comments, oldest first."""
    full_id = _workitem_or_404(project_id, workitem_id)
    comments = data_store.comments.get(full_id, [])
    page_size, page_number = parse_pagination(request.args)
    fields = parse_fields(request.args.get(f"fields[{KIND}]"))
    base_url = base_url_of(request)
    return jsonify(
        {
            "links": pagination_links(request, page_number, page_size, len(comments)),
            "data": [
                _render(full_id, c, base_url, fields)
                for c in paginate(comments, page_size, page_number)
            ],
            "meta": {"totalCount": len(comments)},
        }
    )


@bp.route("/projects/<project_id>/workitems/<workitem_id>/comments", methods=["POST"])
@require_auth
def create_comments(project_id: str, workitem_id: str):
    """Create a list of comments; every entry is checked before any is stored."""
    full_id = _workitem_or_404(project_id, workitem_id)
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("data"), list)
        or not data["data"]
    ):
        raise ValidationError("Request must contain a non-empty 'data' array")
    stored = data_store.comments.setdefault(full_id, [])
    known = {c["id"] for c in stored}
    user = (getattr(g, "current_user", None) or {}).get("user_id") or "admin"
    new: List[Dict[str, Any]] = []
    next_id = max((int(c["id"]) for c in stored), default=0)
    for item in data["data"]:
        if not isinstance(item, dict) or item.get("type") != KIND:
            raise ValidationError(f"Resource type must be '{KIND}'")
        attributes = item.get("attributes") or {}
        text = attributes.get("text")
        if (
            not isinstance(text, dict)
            or text.get("type") not in ("text/html", "text/plain")
            or not isinstance(text.get("value"), str)
        ):
            raise ValidationError(
                "Comment text must be {type: text/html|text/plain, value}", field="text"
            )
        relationships = item.get("relationships") or {}
        parent_ref = ((relationships.get("parentComment") or {}).get("data") or {}).get(
            "id"
        )
        parent = None
        if parent_ref:
            prefix, _, parent = str(parent_ref).rpartition("/")
            if prefix != full_id or parent not in known:
                raise NotFoundError(KIND, str(parent_ref))
        author = ((relationships.get("author") or {}).get("data") or {}).get(
            "id"
        ) or user
        next_id += 1
        comment = {
            "id": str(next_id),
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "text": {"type": text["type"], "value": text["value"]},
            "title": attributes.get("title"),
            "resolved": bool(attributes.get("resolved", False)),
            "author": author,
            "parent": parent,
        }
        known.add(comment["id"])
        new.append(comment)
    stored.extend(new)
    base_url = base_url_of(request)
    logger.info("Created %d comment(s) on %s", len(new), full_id)
    return jsonify(
        {
            "data": [
                {
                    key: value
                    for key, value in _render(full_id, c, base_url).items()
                    if key in ("type", "id", "links")
                }
                for c in new
            ]
        }
    ), 201


@bp.route(
    "/projects/<project_id>/workitems/<workitem_id>/comments/<comment_id>",
    methods=["GET"],
)
@require_auth
def get_comment(project_id: str, workitem_id: str, comment_id: str):
    full_id = _workitem_or_404(project_id, workitem_id)
    comment = _comment_or_404(full_id, comment_id)
    fields = parse_fields(request.args.get(f"fields[{KIND}]"))
    return jsonify(
        {
            "data": _render(full_id, comment, base_url_of(request), fields),
            "links": {"self": request.url},
        }
    )


@bp.route(
    "/projects/<project_id>/workitems/<workitem_id>/comments/<comment_id>",
    methods=["PATCH"],
)
@require_auth
def update_comment(project_id: str, workitem_id: str, comment_id: str):
    """Only ``resolved`` can change (as in the REST API's request schema)."""
    full_id = _workitem_or_404(project_id, workitem_id)
    comment = _comment_or_404(full_id, comment_id)
    data = request.get_json(silent=True)
    item = data.get("data") if isinstance(data, dict) else None
    if not isinstance(item, dict) or item.get("type") != KIND:
        raise ValidationError(f"Request must contain a '{KIND}' resource in 'data'")
    resolved = (item.get("attributes") or {}).get("resolved")
    if not isinstance(resolved, bool):
        raise ValidationError("'resolved' must be true or false", field="resolved")
    comment["resolved"] = resolved
    return "", 204
