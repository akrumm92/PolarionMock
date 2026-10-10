"""
``DELETE /projects/{projectId}/workitems`` - Polarion REST v1 deletes work
items as a list (JSON:API body of ids); a deleted work item also leaves the
document it was part of, in its parts and in its text.
"""

import re
from urllib.parse import quote

import pytest

from .conftest import DOCUMENT, PROJECT, REST_PREFIX, SPACE

pytestmark = [pytest.mark.mock, pytest.mark.unit]

MACRO = re.compile(
    r"polarion_wiki macro name=module-workitem;params=id=([A-Za-z0-9_-]+)"
)
DOC_URL = (
    f"{REST_PREFIX}/projects/{PROJECT}/spaces/{quote(SPACE, safe='')}"
    f"/documents/{DOCUMENT}"
)
LIST_URL = f"{REST_PREFIX}/projects/{PROJECT}/workitems"


@pytest.fixture
def fresh(client, pat_headers):
    client.post("/mock/admin/reset", headers=pat_headers)
    yield
    client.post("/mock/admin/reset", headers=pat_headers)


def ids_body(*short_ids, project=PROJECT):
    return {"data": [{"type": "workitems", "id": f"{project}/{s}"} for s in short_ids]}


def body_macros(client, headers):
    payload = client.get(
        f"{DOC_URL}?fields%5Bdocuments%5D=homePageContent", headers=headers
    ).get_json()
    return MACRO.findall(payload["data"]["attributes"]["homePageContent"]["value"])


def test_delete_a_list_of_work_items(client, pat_headers, fixture_dump, fresh):
    targets = [p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"]][-2:]
    response = client.delete(LIST_URL, headers=pat_headers, json=ids_body(*targets))
    assert response.status_code == 204, response.get_data(as_text=True)
    for short_id in targets:
        assert (
            client.get(f"{LIST_URL}/{short_id}", headers=pat_headers).status_code == 404
        )
        assert short_id not in body_macros(client, pat_headers)
    parts = client.get(
        f"{DOC_URL}/parts?page%5Bsize%5D=100&page%5Bnumber%5D=3", headers=pat_headers
    ).get_json()
    listed = {p["attributes"]["id"] for p in parts["data"]}
    gone = {f"workitem_{t}" for t in targets} | {f"heading_{t}" for t in targets}
    assert not listed & gone
    assert parts["meta"]["totalCount"] == len(fixture_dump["parts"]) - 2


def test_unknown_id_deletes_nothing(client, pat_headers, fixture_dump, fresh):
    known = next(p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"])
    response = client.delete(
        LIST_URL, headers=pat_headers, json=ids_body(known, "VPAT-0")
    )
    assert response.status_code == 404
    assert client.get(f"{LIST_URL}/{known}", headers=pat_headers).status_code == 200


def test_id_of_another_project_is_refused(client, pat_headers, fixture_dump, fresh):
    known = next(p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"])
    response = client.delete(
        LIST_URL, headers=pat_headers, json=ids_body(known, project="Python")
    )
    assert response.status_code == 400
    assert client.get(f"{LIST_URL}/{known}", headers=pat_headers).status_code == 200


def test_empty_list_is_refused(client, pat_headers):
    response = client.delete(LIST_URL, headers=pat_headers, json={"data": []})
    assert response.status_code == 400
