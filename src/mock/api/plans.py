"""
Plans (Polarion REST v1, read only).

``GET /projects/{p}/plans``           list (paged, ``query``, ``templates``)
``GET /projects/{p}/plans/{planId}``  one plan

As the spec says, ``templates=true`` lists only templates, otherwise only
actual instances are listed. Data: ``storage/demo_seed.py``.
"""

from typing import Any, Dict

from flask import Blueprint, request

from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError
from ..storage.data_store import data_store
from ..storage.demo_seed import DEMO_AUTHOR, DEMO_CREATED
from ..utils import lucene
from ..utils.listing import fields_of, list_response, project_url
from ..utils.listing import require_project, single_response
from ..utils.parts import apply_fields

bp = Blueprint("plans", __name__)

_ATTRIBUTES = ("id", "name", "isTemplate", "status", "startDate", "dueDate")


def _attributes(plan: Dict[str, Any]) -> Dict[str, Any]:
    attributes = {key: plan[key] for key in _ATTRIBUTES if plan[key] is not None}
    attributes.update(
        calculationType="timeBased", created=DEMO_CREATED, updated=DEMO_CREATED
    )
    return attributes


def _to_one(kind: str, full_id: str) -> Dict[str, Any]:
    return {"data": {"type": kind, "id": full_id}}


def _render(plan: Dict[str, Any]) -> Dict[str, Any]:
    project_id = plan["project"]
    relationships = {
        "author": _to_one("users", DEMO_AUTHOR),
        "project": _to_one("projects", project_id),
        "workItems": {
            "data": [{"type": "workitems", "id": i} for i in plan["workitems"]],
            "meta": {"totalCount": len(plan["workitems"])},
        },
    }
    for name in ("template", "parent"):
        if plan[name]:
            relationships[name] = _to_one("plans", f"{project_id}/{plan[name]}")
    return {
        "type": "plans",
        "id": f"{project_id}/{plan['id']}",
        "attributes": apply_fields(_attributes(plan), fields_of("plans")),
        "relationships": relationships,
        "links": {"self": project_url(project_id, "plans", plan["id"])},
    }


@bp.route("/projects/<project_id>/plans", methods=["GET"])
@require_auth
def list_plans(project_id: str):
    require_project(project_id)
    templates = request.args.get("templates", "").lower() == "true"
    query = request.args.get("query")
    plans = [
        plan
        for plan in data_store.plans.values()
        if plan["project"] == project_id
        and plan["isTemplate"] == templates
        and lucene.matches(_attributes(plan), query)
    ]
    return list_response(plans, _render)


@bp.route("/projects/<project_id>/plans/<plan_id>", methods=["GET"])
@require_auth
def get_plan(project_id: str, plan_id: str):
    require_project(project_id)
    plan = data_store.plans.get(f"{project_id}/{plan_id}")
    if plan is None:
        raise NotFoundError("plans", f"{project_id}/{plan_id}")
    return single_response(_render(plan))
