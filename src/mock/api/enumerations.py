"""
Enumerations (Polarion REST v1, read only).

``GET /projects/{p}/enumerations/{enumContext}/{enumName}/{targetType}``
    one project enumeration
``GET /projects/{p}/workitems/{wi}/fields/{fieldId}/actions/getAvailableOptions``
    the options a field of that work item may take (paged)

Sources: the enumerations of the exported data model (see
``storage/data_model.py``); ``status`` is derived from the statuses the
project's work items of that type carry (the export has no status ids);
``workitem-link-role`` offers generic default roles (the export has none);
user fields (``assignee``, ``enum:@user`` custom fields) offer the users.
"""

from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify

from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError, ValidationError
from ..storage import data_model
from ..storage.data_store import data_store
from ..utils.listing import list_response, project_url, require_project
from ..utils.listing import require_workitem

bp = Blueprint("enumerations", __name__)

ENUM_CONTEXTS = ("~", "plans", "testing", "documents")
# built-in work item fields that are enumerations, and the enumeration
_BUILT_IN_ENUM_FIELDS = {"type": "workitem-type", "severity": "severity"}
_BUILT_IN_USER_FIELDS = ("assignee", "author")
# The data model export carries no link roles: generic roles of a default
# Polarion project (role id, name, opposite name).
DEFAULT_LINK_ROLES = [
    {"id": "relates_to", "name": "relates to", "oppositeName": "is related to"},
    {"id": "parent", "name": "has parent", "oppositeName": "is parent of"},
    {"id": "depends_on", "name": "depends on", "oppositeName": "is required by"},
    {"id": "duplicates", "name": "duplicates", "oppositeName": "is duplicated by"},
    {"id": "verifies", "name": "verifies", "oppositeName": "is verified by"},
]
_BUILT_IN_PLAIN_FIELDS = (
    "id",
    "title",
    "description",
    "outlineNumber",
    "created",
    "updated",
    "dueDate",
    "resolvedOn",
)


# Placeholder - will be implemented later
@bp.route("/enumerations", methods=["GET"])
def list_enumerations():
    """List all enumerations."""
    return {"message": "Enumerations endpoint not yet implemented"}, 501


def status_options(project_id: str, type_id: str) -> List[Dict[str, Any]]:
    """Statuses the project's work items of ``type_id`` (``~`` = any) carry."""
    seen: List[str] = []
    for item in data_store.workitems.values():
        if not item.id.startswith(f"{project_id}/"):
            continue
        if type_id != "~" and item.attributes.type != type_id:
            continue
        status = item.attributes.status
        if status and status not in seen:
            seen.append(status)
    return [{"id": status, "name": status} for status in seen]


def _user_options() -> List[Dict[str, Any]]:
    users = sorted(data_store.users.values(), key=lambda u: u.id)
    return [{"id": u.id, "name": u.attributes.name} for u in users]


def _enumeration_options(project_id: str, name: str, target: str) -> List[Dict]:
    if name == "status":
        options = status_options(project_id, target)
        if not options:
            raise NotFoundError("enumerations", f"{project_id}/~/{name}/{target}")
        return options
    if name == "workitem-link-role":
        return DEFAULT_LINK_ROLES
    options = data_model.enumeration(name)
    if options is None:
        raise NotFoundError("enumerations", f"{project_id}/~/{name}/{target}")
    return options


@bp.route(
    "/projects/<project_id>/enumerations/<enum_context>/<enum_name>/<target_type>",
    methods=["GET"],
)
@require_auth
def get_project_enumeration(
    project_id: str, enum_context: str, enum_name: str, target_type: str
):
    require_project(project_id)
    if enum_context not in ENUM_CONTEXTS:
        raise ValidationError(
            f"Unknown enumeration context '{enum_context}' "
            f"(allowed: {', '.join(ENUM_CONTEXTS)})"
        )
    full_id = f"{project_id}/{enum_context}/{enum_name}/{target_type}"
    if enum_context != "~":
        raise NotFoundError("enumerations", full_id)
    options = _enumeration_options(project_id, enum_name, target_type)
    self_link = project_url(
        project_id, "enumerations", enum_context, enum_name, target_type
    )
    resource = {
        "type": "enumerations",
        "id": full_id,
        "attributes": {
            "enumContext": enum_context,
            "enumName": enum_name,
            "targetType": target_type,
            "options": list(options),
        },
        "links": {"self": self_link},
    }
    return jsonify({"data": resource, "links": {"self": self_link}})


def _field_options(
    project_id: str, type_id: str, field_id: str
) -> Optional[List[Dict[str, Any]]]:
    """Options of ``field_id``; ``None`` if the field is not an enumeration."""
    if field_id == "status":
        return status_options(project_id, type_id)
    if field_id in _BUILT_IN_ENUM_FIELDS:
        return data_model.enumeration(_BUILT_IN_ENUM_FIELDS[field_id]) or []
    if field_id in _BUILT_IN_USER_FIELDS:
        return _user_options()
    if field_id in _BUILT_IN_PLAIN_FIELDS:
        return None
    definition = data_model.custom_fields(type_id).get(field_id)
    if definition is None:
        raise NotFoundError("fields", f"{type_id}/{field_id}")
    kind = definition.get("type", "")
    if kind.startswith("enum:@user"):
        return _user_options()
    if kind.startswith("enum:"):
        return data_model.enumeration(kind[len("enum:") :]) or []
    return None


@bp.route(
    "/projects/<project_id>/workitems/<workitem_id>/fields/<field_id>"
    "/actions/getAvailableOptions",
    methods=["GET"],
)
@require_auth
def get_available_options(project_id: str, workitem_id: str, field_id: str):
    full_id = require_workitem(project_id, workitem_id)
    type_id = data_store.workitems[full_id].attributes.type
    options = _field_options(project_id, type_id, field_id)
    if options is None:
        raise ValidationError(f"Field '{field_id}' of {full_id} is not an enumeration")
    return list_response(list(options), lambda option: option)
