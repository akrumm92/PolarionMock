"""
Workflow actions of a work item (Polarion REST v1, read only).

``GET /projects/{p}/workitems/{wi}/actions/getWorkflowActions``  (paged)

The mock holds no workflow configuration. It offers one action per other
status known for the item's type (see ``enumerations.status_options``): the
action ``set_<status>`` leads to that status, needs no fields, roles or
signature.
"""

from flask import Blueprint

from ..middleware.auth import require_auth
from ..storage.data_store import data_store
from ..utils.listing import list_response, require_workitem
from .enumerations import status_options

bp = Blueprint("workflow_actions", __name__)


def _action(status: dict) -> dict:
    action_id = f"set_{status['id']}"
    return {
        "id": action_id,
        "nativeActionId": action_id,
        "name": f"Set {status['name']}",
        "targetStatus": status["id"],
        "available": True,
        "requiredFields": [],
        "requiredRoles": [],
        "clearedFields": [],
        "isSignatureRequired": False,
        "isAddingSignature": False,
    }


@bp.route(
    "/projects/<project_id>/workitems/<workitem_id>/actions/getWorkflowActions",
    methods=["GET"],
)
@require_auth
def get_workflow_actions(project_id: str, workitem_id: str):
    full_id = require_workitem(project_id, workitem_id)
    attributes = data_store.workitems[full_id].attributes
    actions = [
        _action(status)
        for status in status_options(project_id, attributes.type)
        if status["id"] != attributes.status
    ]
    return list_response(actions, lambda action: action)
