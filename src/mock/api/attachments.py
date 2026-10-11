"""
Attachments of work items, documents and test runs (Polarion REST v1, read).

``GET {owner}/attachments``                         list (paged)
``GET {owner}/attachments/{attachmentId}/content``  the file
    (``application/octet-stream``, as the spec says)

``{owner}`` is ``/projects/{p}/workitems/{wi}``,
``/projects/{p}/spaces/{space}/documents/{name}`` or
``/projects/{p}/testruns/{testRunId}``. Data: ``storage/demo_seed.py``.
"""

from typing import Any, Dict, List, Tuple

from flask import Blueprint, Response

from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError
from ..storage.data_store import data_store
from ..storage.demo_seed import DEMO_AUTHOR, DEMO_CREATED, attachment_key
from ..utils.listing import fields_of, list_response, project_url
from ..utils.listing import require_project, require_workitem
from ..utils.parts import apply_fields

bp = Blueprint("attachments", __name__)

WORKITEM = "/projects/<project_id>/workitems/<workitem_id>/attachments"
DOCUMENT = "/projects/<project_id>/spaces/<space_id>/documents/<name>/attachments"
TESTRUN = "/projects/<project_id>/testruns/<run_id>/attachments"


def _workitem(project_id: str, workitem_id: str) -> Tuple[str, str, List[str]]:
    full_id = require_workitem(project_id, workitem_id)
    return "workitem", full_id, ["workitems", workitem_id]


def _document(project_id: str, space_id: str, name: str) -> Tuple[str, str, List]:
    require_project(project_id)
    full_id = f"{project_id}/{space_id}/{name}"
    if full_id not in data_store.documents:
        raise NotFoundError("documents", full_id)
    return "document", full_id, ["spaces", space_id, "documents", name]


def _testrun(project_id: str, run_id: str) -> Tuple[str, str, List[str]]:
    require_project(project_id)
    full_id = f"{project_id}/{run_id}"
    if full_id not in data_store.testruns:
        raise NotFoundError("testruns", full_id)
    return "testrun", full_id, ["testruns", run_id]


def _list(project_id: str, owner: Tuple[str, str, List[str]]):
    kind, owner_id, segments = owner
    attachments = data_store.attachments.get(attachment_key(kind, owner_id), [])
    fields = fields_of(f"{kind}_attachments")

    def render(attachment: Dict[str, Any]) -> Dict[str, Any]:
        attributes = {
            "id": attachment["id"],
            "fileName": attachment["fileName"],
            "title": attachment["title"],
            "length": len(attachment["content"]),
            "updated": DEMO_CREATED,
        }
        self_link = project_url(project_id, *segments, "attachments", attachment["id"])
        return {
            "type": f"{kind}_attachments",
            "id": f"{owner_id}/{attachment['id']}",
            "attributes": apply_fields(attributes, fields),
            "relationships": {
                "author": {"data": {"type": "users", "id": DEMO_AUTHOR}},
                "project": {"data": {"type": "projects", "id": project_id}},
            },
            "links": {"self": self_link, "content": f"{self_link}/content"},
        }

    return list_response(list(attachments), render)


def _content(owner: Tuple[str, str, List[str]], attachment_id: str) -> Response:
    kind, owner_id, _ = owner
    for attachment in data_store.attachments.get(attachment_key(kind, owner_id), []):
        if attachment["id"] == attachment_id:
            return Response(attachment["content"], mimetype="application/octet-stream")
    raise NotFoundError(f"{kind}_attachments", f"{owner_id}/{attachment_id}")


@bp.route(WORKITEM, methods=["GET"])
@require_auth
def list_workitem_attachments(project_id: str, workitem_id: str):
    return _list(project_id, _workitem(project_id, workitem_id))


@bp.route(f"{WORKITEM}/<attachment_id>/content", methods=["GET"])
@require_auth
def workitem_attachment_content(project_id: str, workitem_id: str, attachment_id: str):
    return _content(_workitem(project_id, workitem_id), attachment_id)


@bp.route(DOCUMENT, methods=["GET"])
@require_auth
def list_document_attachments(project_id: str, space_id: str, name: str):
    return _list(project_id, _document(project_id, space_id, name))


@bp.route(f"{DOCUMENT}/<attachment_id>/content", methods=["GET"])
@require_auth
def document_attachment_content(
    project_id: str, space_id: str, name: str, attachment_id: str
):
    return _content(_document(project_id, space_id, name), attachment_id)


@bp.route(TESTRUN, methods=["GET"])
@require_auth
def list_testrun_attachments(project_id: str, run_id: str):
    return _list(project_id, _testrun(project_id, run_id))


@bp.route(f"{TESTRUN}/<attachment_id>/content", methods=["GET"])
@require_auth
def testrun_attachment_content(project_id: str, run_id: str, attachment_id: str):
    return _content(_testrun(project_id, run_id), attachment_id)
