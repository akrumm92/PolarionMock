"""GET .../workitems/{wi}/actions/getWorkflowActions."""

import pytest

from .conftest import PROJECT, REST_PREFIX, assert_matches_schema

pytestmark = pytest.mark.mock


def actions_url(workitem_id: str) -> str:
    return (f"{REST_PREFIX}/projects/{PROJECT}/workitems/{workitem_id}"
            "/actions/getWorkflowActions")


@pytest.mark.parametrize("workitem_id, target", [
    ("VPAT-11134", "proposed"),   # a draft system requirement
    ("VPAT-11153", "draft"),      # a proposed system requirement
])
def test_actions_lead_to_the_other_statuses(client, pat_headers, workitem_id, target):
    response = client.get(actions_url(workitem_id), headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("workflowActionsActionResponseBody", payload)
    assert [a["targetStatus"] for a in payload["data"]] == [target]
    action = payload["data"][0]
    assert action["id"] == f"set_{target}" and action["available"] is True
    assert payload["meta"]["totalCount"] == 1


def test_unknown_work_item_is_404(client, pat_headers):
    response = client.get(actions_url("VPAT-1"), headers=pat_headers)
    assert response.status_code == 404
    assert "VPATHAI/VPAT-1'" in response.get_json()["errors"][0]["detail"]
