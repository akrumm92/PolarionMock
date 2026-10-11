"""Project enumerations and a work item field's available options."""

import pytest

from .conftest import PROJECT, REST_PREFIX, assert_matches_schema

pytestmark = pytest.mark.mock

ENUMS = f"{REST_PREFIX}/projects/{PROJECT}/enumerations"
ITEM = f"{REST_PREFIX}/projects/{PROJECT}/workitems/VPAT-11134"


def options_url(field: str) -> str:
    return f"{ITEM}/fields/{field}/actions/getAvailableOptions"


def test_workitem_types_come_from_the_data_model(client, pat_headers):
    response = client.get(f"{ENUMS}/~/workitem-type/~", headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("enumerationsSingleGetResponse", payload)
    data = payload["data"]
    assert data["id"] == f"{PROJECT}/~/workitem-type/~"
    ids = [option["id"] for option in data["attributes"]["options"]]
    assert ids[:2] == ["information", "productrequirement"]
    assert {"systemrequirement", "componentrequirement", "userstory"} <= set(ids)


def test_status_enumeration_is_derived_from_the_work_items(client, pat_headers):
    payload = client.get(f"{ENUMS}/~/status/systemrequirement",
                         headers=pat_headers).get_json()
    options = payload["data"]["attributes"]["options"]
    assert {option["id"] for option in options} == {"draft", "proposed"}


def test_link_roles_are_offered(client, pat_headers):
    payload = client.get(f"{ENUMS}/~/workitem-link-role/~", headers=pat_headers).get_json()
    assert_matches_schema("enumerationsSingleGetResponse", payload)
    roles = {o["id"]: o for o in payload["data"]["attributes"]["options"]}
    assert roles["relates_to"]["oppositeName"] == "is related to"
    assert "parent" in roles


@pytest.mark.parametrize("path, status, detail", [
    ("~/no-such-enum/~", 404, "enumerations with id 'VPATHAI/~/no-such-enum/~'"),
    ("plans/status/~", 404, "enumerations with id 'VPATHAI/plans/status/~'"),
    ("bogus/status/~", 400, "Unknown enumeration context 'bogus'"),
])
def test_unknown_enumerations_are_refused(client, pat_headers, path, status, detail):
    response = client.get(f"{ENUMS}/{path}", headers=pat_headers)
    assert response.status_code == status
    assert_matches_schema("errors", response.get_json())
    assert detail in response.get_json()["errors"][0]["detail"]


def test_unknown_project_is_404(client, pat_headers):
    url = f"{REST_PREFIX}/projects/NOPE/enumerations/~/workitem-type/~"
    response = client.get(url, headers=pat_headers)
    assert response.status_code == 404
    assert response.get_json()["errors"][0]["detail"] == "Project id NOPE does not exist."


def test_custom_enum_field_offers_the_enum_options(client, pat_headers):
    response = client.get(options_url("requirementtype"), headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("enumOptionsActionResponseBody", payload)
    assert [o["id"] for o in payload["data"]] == [
        "functionalrequirement", "qualityrequirement", "constraint"]
    assert payload["meta"]["totalCount"] == 3


def test_field_options_are_paged(client, pat_headers):
    url = options_url("type") + "?page%5Bsize%5D=5&page%5Bnumber%5D=2"
    payload = client.get(url, headers=pat_headers).get_json()
    assert len(payload["data"]) == 5 and payload["meta"]["totalCount"] > 5
    assert "next" in payload["links"]


def test_status_and_user_fields(client, pat_headers):
    status = client.get(options_url("status"), headers=pat_headers).get_json()
    assert {o["id"] for o in status["data"]} == {"draft", "proposed"}
    users = client.get(options_url("assignee"), headers=pat_headers).get_json()
    assert "admin" in [o["id"] for o in users["data"]]


@pytest.mark.parametrize("field, status, detail", [
    ("title", 400, "Field 'title' of VPATHAI/VPAT-11134 is not an enumeration"),
    ("no_such_field", 404, "fields with id 'systemrequirement/no_such_field'"),
])
def test_non_enum_and_unknown_fields(client, pat_headers, field, status, detail):
    response = client.get(options_url(field), headers=pat_headers)
    assert response.status_code == status
    assert_matches_schema("errors", response.get_json())
    assert detail in response.get_json()["errors"][0]["detail"]


def test_unknown_work_item_is_404(client, pat_headers):
    url = (f"{REST_PREFIX}/projects/{PROJECT}/workitems/VPAT-1"
           "/fields/type/actions/getAvailableOptions")
    response = client.get(url, headers=pat_headers)
    assert response.status_code == 404
    assert "VPATHAI/VPAT-1'" in response.get_json()["errors"][0]["detail"]
