"""
Loading Polarion document dumps (exports of the fetch script) into the mock:
at start-up from ``src/mock/mock_data/polarion_dumps`` and at runtime via
``POST /mock/admin/dumps``.
"""

import copy

import pytest

from src.mock.storage.dump_loader import DumpFormatError, validate_dump

from .conftest import REST_PREFIX

pytestmark = [pytest.mark.mock, pytest.mark.unit]

SMALL_DUMP = {
    "document": {"name": "Tiny Spec", "project": "DEMO", "space": "Sub Space",
                 "base_url": "https://example", "fetched_at": "2026-01-01T00:00:00Z",
                 "part_count": 3, "part_count_reported": 3, "work_item_count": 2},
    "parts": [
        {"part_id": "heading_DEMO-1", "part_type": "heading",
         "content_html": "<h1 id=\"polarion_wiki macro name=module-workitem;params=id=DEMO-1\"></h1>",
         "workitem_id": "DEMO-1"},
        {"part_id": "polarion_1", "part_type": "normal", "content_html": "<p id=\"polarion_1\"></p>",
         "workitem_id": None},
        {"part_id": "workitem_DEMO-2", "part_type": "workitem",
         "content_html": "<div id=\"polarion_wiki macro name=module-workitem;params=id=DEMO-2\"></div>",
         "workitem_id": "DEMO-2"},
    ],
    "workitems": [
        {"id": "DEMO-1", "title": "Tiny Spec", "type": "heading", "outlineNumber": None,
         "status": "proposed", "description_html": ""},
        {"id": "DEMO-2", "title": "Ein Ärger-freies Requirement", "type": "systemrequirement",
         "outlineNumber": "1-1", "status": "draft", "description_html": "<p>Muss ü können.</p>"},
    ],
}


def test_bundled_dump_is_loaded_at_startup(client, pat_headers):
    payload = client.get("/mock/admin/dumps", headers=pat_headers).get_json()
    ids = [d["document_id"] for d in payload["dumps"]]
    assert "VPATHAI/System Layer/Technical_Specification-API_TEST" in ids
    loaded = next(d for d in payload["dumps"] if d["document_id"].startswith("VPATHAI/"))
    assert loaded["parts"] == 218 and loaded["workitems"] == 158


def test_dump_can_be_loaded_at_runtime(client, pat_headers):
    response = client.post("/mock/admin/dumps", json=SMALL_DUMP, headers=pat_headers)
    assert response.status_code == 201, response.get_data(as_text=True)
    assert response.get_json()["data"]["document_id"] == "DEMO/Sub Space/Tiny Spec"

    parts = client.get(f"{REST_PREFIX}/projects/DEMO/spaces/Sub%20Space/documents/Tiny%20Spec/parts"
                       "?fields%5Bdocument_parts%5D=%40all", headers=pat_headers).get_json()
    assert parts["meta"]["totalCount"] == 3
    assert [p["attributes"]["id"] for p in parts["data"]] == ["heading_DEMO-1", "polarion_1", "workitem_DEMO-2"]
    assert parts["data"][2]["relationships"]["workItem"]["data"]["id"] == "DEMO/DEMO-2"

    workitem = client.get(f"{REST_PREFIX}/projects/DEMO/workitems/DEMO-2?fields%5Bworkitems%5D=%40all",
                          headers=pat_headers).get_json()["data"]
    assert workitem["attributes"]["title"] == "Ein Ärger-freies Requirement"
    assert workitem["attributes"]["description"] == {"type": "text/html", "value": "<p>Muss ü können.</p>"}
    assert workitem["attributes"]["outlineNumber"] == "1-1"

    project = client.get(f"{REST_PREFIX}/projects/DEMO", headers=pat_headers).get_json()["data"]
    assert project["attributes"]["trackerPrefix"] == "DEMO"


def test_reloading_the_same_document_replaces_it(client, pat_headers):
    client.post("/mock/admin/dumps", json=SMALL_DUMP, headers=pat_headers)
    changed = copy.deepcopy(SMALL_DUMP)
    changed["parts"] = changed["parts"][:1]
    changed["workitems"] = changed["workitems"][:1]
    client.post("/mock/admin/dumps", json=changed, headers=pat_headers)

    parts = client.get(f"{REST_PREFIX}/projects/DEMO/spaces/Sub%20Space/documents/Tiny%20Spec/parts",
                       headers=pat_headers).get_json()
    assert parts["meta"]["totalCount"] == 1
    assert client.get(f"{REST_PREFIX}/projects/DEMO/workitems/DEMO-2", headers=pat_headers).status_code == 404


def test_reset_restores_the_bundled_state(client, pat_headers):
    client.post("/mock/admin/dumps", json=SMALL_DUMP, headers=pat_headers)
    response = client.post("/mock/admin/reset", headers=pat_headers)
    assert response.status_code == 200
    assert client.get(f"{REST_PREFIX}/projects/DEMO", headers=pat_headers).status_code == 404
    health = client.get("/health").get_json()
    assert health["dumps"] == ["VPATHAI/System Layer/Technical_Specification-API_TEST"]


def test_invalid_dump_is_rejected(client, pat_headers):
    response = client.post("/mock/admin/dumps", json={"document": {}}, headers=pat_headers)
    assert response.status_code == 400
    with pytest.raises(DumpFormatError):
        validate_dump({"document": {"name": "x", "project": "p", "space": "s"}, "parts": "no", "workitems": []})


def test_documents_overview_lists_coordinates(client, pat_headers):
    payload = client.get("/mock/admin/documents", headers=pat_headers).get_json()
    entry = next(d for d in payload["data"] if d["id"] == "VPATHAI/System Layer/Technical_Specification-API_TEST")
    assert entry["project"] == "VPATHAI" and entry["space"] == "System Layer"
    assert entry["parts"] == 218 and entry["workitems"] == 158
    assert entry["parts_url"].endswith("/spaces/System%20Layer/documents/Technical_Specification-API_TEST/parts")
