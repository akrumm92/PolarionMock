"""Attachments of work items, documents and test runs, and their content."""

import pytest

from .conftest import DOCUMENT, PROJECT, REST_PREFIX, assert_matches_schema

pytestmark = pytest.mark.mock

BASE = f"{REST_PREFIX}/projects/{PROJECT}"
OWNERS = [
    (f"{BASE}/workitems/VPAT-11138", "workitem", f"{PROJECT}/VPAT-11138"),
    (f"{BASE}/spaces/System%20Layer/documents/{DOCUMENT}", "document",
     f"{PROJECT}/System Layer/{DOCUMENT}"),
    (f"{BASE}/testruns/TestRun_1", "testrun", f"{PROJECT}/TestRun_1"),
]


@pytest.mark.parametrize("owner, kind, owner_id", OWNERS)
def test_attachments_are_listed(client, pat_headers, owner, kind, owner_id):
    response = client.get(f"{owner}/attachments", headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema(f"{kind}_attachmentsListGetResponse", payload)
    assert payload["meta"]["totalCount"] == 1
    attachment = payload["data"][0]
    assert attachment["type"] == f"{kind}_attachments"
    assert attachment["id"] == f"{owner_id}/1-notes.txt"
    assert attachment["links"]["content"].endswith("/attachments/1-notes.txt/content")


@pytest.mark.parametrize("owner, kind, owner_id", OWNERS)
def test_attachment_content(client, owner, kind, owner_id, fake_pat):
    headers = {"Authorization": f"Bearer {fake_pat}", "Accept": "*/*"}
    response = client.get(f"{owner}/attachments/1-notes.txt/content", headers=headers)
    assert response.status_code == 200
    assert response.mimetype == "application/octet-stream"
    assert response.get_data(as_text=True) == f"Demo attachment of {kind} {owner_id}.\n"


def test_length_and_sparse_fields(client, pat_headers):
    url = (f"{BASE}/workitems/VPAT-11138/attachments"
           "?fields%5Bworkitem_attachments%5D=fileName%2Clength")
    attributes = client.get(url, headers=pat_headers).get_json()["data"][0]["attributes"]
    expected = len(f"Demo attachment of workitem {PROJECT}/VPAT-11138.\n")
    assert attributes == {"fileName": "notes.txt", "length": expected}


def test_item_without_attachments_answers_an_empty_list(client, pat_headers):
    payload = client.get(f"{BASE}/workitems/VPAT-11134/attachments",
                         headers=pat_headers).get_json()
    assert payload["data"] == [] and payload["meta"]["totalCount"] == 0


@pytest.mark.parametrize("url, detail", [
    (f"{BASE}/workitems/VPAT-11138/attachments/nope/content",
     "workitem_attachments with id 'VPATHAI/VPAT-11138/nope'"),
    (f"{BASE}/workitems/VPAT-1/attachments", "VPATHAI/VPAT-1'"),
    (f"{BASE}/spaces/System%20Layer/documents/Nope/attachments",
     "documents with id 'VPATHAI/System Layer/Nope'"),
    (f"{BASE}/testruns/nope/attachments", "testruns with id 'VPATHAI/nope'"),
])
def test_unknown_owner_or_attachment_is_404(client, pat_headers, url, detail):
    response = client.get(url, headers=pat_headers)
    assert response.status_code == 404
    assert detail in response.get_json()["errors"][0]["detail"]
