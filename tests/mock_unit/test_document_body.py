"""
A LiveDoc's text (``homePageContent``) and its parts are one thing: the parts
list is a view of the text, so every reader sees the same document whichever
of the two it reads, and every writer changes both.
"""

import re
from urllib.parse import quote

import pytest

from src.mock.storage.document_body import render_body, split_body

from .conftest import DOCUMENT, PROJECT, REST_PREFIX, SPACE

pytestmark = [pytest.mark.mock, pytest.mark.unit]

MACRO = re.compile(
    r"polarion_wiki macro name=module-workitem;params=id=([A-Za-z0-9_-]+)"
)
DOC_URL = (
    f"{REST_PREFIX}/projects/{PROJECT}/spaces/{quote(SPACE, safe='')}"
    f"/documents/{DOCUMENT}"
)
SANDBOX_URL = (
    f"{REST_PREFIX}/projects/TestProject/spaces/TestSpace/documents/TestDocument"
)


@pytest.fixture
def fresh(client, pat_headers):
    """Tests that write start and end on the bundled state."""
    client.post("/mock/admin/reset", headers=pat_headers)
    yield
    client.post("/mock/admin/reset", headers=pat_headers)


def body_of(client, headers, url=DOC_URL) -> str:
    response = client.get(
        f"{url}?fields%5Bdocuments%5D=homePageContent", headers=headers
    )
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    content = response.get_json()["data"]["attributes"]["homePageContent"]
    assert content["type"] == "text/html"
    return content["value"]


def part_ids(client, headers, url=DOC_URL) -> list:
    response = client.get(f"{url}/parts?page%5Bsize%5D=100", headers=headers)
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    ids = [p["attributes"]["id"] for p in payload["data"]]
    total = payload["meta"]["totalCount"]
    page = 2
    while len(ids) < total:
        more = client.get(
            f"{url}/parts?page%5Bsize%5D=100&page%5Bnumber%5D={page}", headers=headers
        ).get_json()["data"]
        ids += [p["attributes"]["id"] for p in more]
        page += 1
    return ids


def test_recorded_parts_split_back_into_the_same_parts(fixture_dump):
    body = render_body([part["content_html"] for part in fixture_dump["parts"]])
    parts = split_body(body, PROJECT)
    assert [(p["id"], p["type"], p["content"]) for p in parts] == [
        (p["part_id"], p["part_type"], p["content_html"]) for p in fixture_dump["parts"]
    ]
    assert [p["workitem_id"] for p in parts] == [
        f"{PROJECT}/{p['workitem_id']}" if p["workitem_id"] else None
        for p in fixture_dump["parts"]
    ]


def test_text_of_a_loaded_dump_carries_every_part(client, pat_headers, fixture_dump):
    body = body_of(client, pat_headers)
    assert body == render_body([part["content_html"] for part in fixture_dump["parts"]])
    referenced = [p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"]]
    assert MACRO.findall(body) == referenced


def test_posting_a_part_puts_its_macro_into_the_text(client, pat_headers, fresh):
    created = client.post(
        f"{REST_PREFIX}/projects/TestProject/workitems",
        headers=pat_headers,
        json={
            "data": [
                {
                    "type": "workitems",
                    "attributes": {"title": "New", "type": "requirement"},
                    "relationships": {
                        "module": {
                            "data": {
                                "type": "documents",
                                "id": "TestProject/TestSpace/TestDocument",
                            }
                        }
                    },
                }
            ]
        },
    )
    assert created.status_code == 201
    short_id = created.get_json()["data"][0]["id"].split("/")[-1]
    assert short_id not in MACRO.findall(body_of(client, pat_headers, SANDBOX_URL))

    posted = client.post(
        f"{SANDBOX_URL}/parts",
        headers=pat_headers,
        json={
            "data": [
                {
                    "type": "document_parts",
                    "attributes": {"type": "workitem"},
                    "relationships": {
                        "workItem": {
                            "data": {
                                "type": "workitems",
                                "id": f"TestProject/{short_id}",
                            }
                        }
                    },
                }
            ]
        },
    )
    assert posted.status_code == 201, posted.get_data(as_text=True)
    assert MACRO.findall(body_of(client, pat_headers, SANDBOX_URL)) == [short_id]
    assert part_ids(client, pat_headers, SANDBOX_URL)[-1] == f"workitem_{short_id}"


def test_writing_the_text_rewrites_the_parts(client, pat_headers, fixture_dump, fresh):
    blocks = [part["content_html"] for part in fixture_dump["parts"]]
    gone = next(p for p in fixture_dump["parts"] if p["part_type"] == "workitem")
    first_heading = next(
        p for p in fixture_dump["parts"] if p["part_type"] == "heading"
    )
    kept = [b for b in blocks if b != gone["content_html"]]
    kept.remove(first_heading["content_html"])
    kept.append(first_heading["content_html"])  # the first heading moves to the end

    response = client.patch(
        DOC_URL,
        headers=pat_headers,
        json={
            "data": {
                "type": "documents",
                "id": f"{PROJECT}/{SPACE}/{DOCUMENT}",
                "attributes": {
                    "homePageContent": {"type": "text/html", "value": render_body(kept)}
                },
            }
        },
    )
    assert response.status_code in (200, 204), response.get_data(as_text=True)

    ids = part_ids(client, pat_headers)
    assert gone["part_id"] not in ids
    assert ids[-1] == first_heading["part_id"]
    assert len(ids) == len(fixture_dump["parts"]) - 1
    assert body_of(client, pat_headers) == render_body(kept)
    states = client.get(
        f"{REST_PREFIX}/mock/debug/workitem-states/{PROJECT}/{gone['workitem_id']}",
        headers=pat_headers,
    ).get_json()
    assert states["in_document"] is False and states["in_recycle_bin"] is True


def test_text_naming_an_unknown_work_item_is_refused(client, pat_headers, fresh):
    before = body_of(client, pat_headers, SANDBOX_URL)
    text = (
        before
        + '\n<div id="polarion_wiki macro name=module-workitem;params=id=TP-99999"></div>'
    )
    response = client.patch(
        SANDBOX_URL,
        headers=pat_headers,
        json={
            "data": {
                "type": "documents",
                "id": "TestProject/TestSpace/TestDocument",
                "attributes": {"homePageContent": {"type": "text/html", "value": text}},
            }
        },
    )
    assert response.status_code == 400
    assert "TP-99999" in response.get_data(as_text=True)
    assert body_of(client, pat_headers, SANDBOX_URL) == before


def test_parts_listing_refuses_a_block_without_id(client, pat_headers, fresh):
    response = client.patch(
        SANDBOX_URL,
        headers=pat_headers,
        json={
            "data": {
                "type": "documents",
                "id": "TestProject/TestSpace/TestDocument",
                "attributes": {
                    "homePageContent": {"type": "text/html", "value": "<p>no id</p>"}
                },
            }
        },
    )
    assert response.status_code in (200, 204)
    assert body_of(client, pat_headers, SANDBOX_URL) == "<p>no id</p>"
    assert client.get(f"{SANDBOX_URL}/parts", headers=pat_headers).status_code == 500
