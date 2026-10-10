"""
Work item links as Polarion REST v1 has them: ``.../linkedworkitems`` lists,
creates and deletes (as a list) the links stored on a work item; links that
point TO a work item are its ``backlinkedWorkItems`` relationship - REST v1
has no ``.../backlinkedworkitems`` endpoint.
"""

import pytest

from .conftest import PROJECT, REST_PREFIX

pytestmark = [pytest.mark.mock, pytest.mark.unit]

WI_URL = f"{REST_PREFIX}/projects/{PROJECT}/workitems"


@pytest.fixture
def fresh(client, pat_headers):
    client.post("/mock/admin/reset", headers=pat_headers)
    yield
    client.post("/mock/admin/reset", headers=pat_headers)


@pytest.fixture
def pair(fixture_dump):
    items = [p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"]]
    return items[1], items[2]


def link(client, headers, source, target, role="relates_to"):
    return client.post(
        f"{WI_URL}/{source}/linkedworkitems",
        headers=headers,
        json={
            "data": [
                {
                    "type": "linkedworkitems",
                    "attributes": {"role": role},
                    "relationships": {
                        "workItem": {
                            "data": {"type": "workitems", "id": f"{PROJECT}/{target}"}
                        }
                    },
                }
            ]
        },
    )


def outgoing(client, headers, source):
    response = client.get(
        f"{WI_URL}/{source}/linkedworkitems?fields%5Blinkedworkitems%5D=%40all"
        "&page%5Bsize%5D=100&page%5Bnumber%5D=1",
        headers=headers,
    )
    assert response.status_code == 200
    return response.get_json()


def backlinks(client, headers, target, fields="%40all"):
    response = client.get(
        f"{WI_URL}/{target}?fields%5Bworkitems%5D={fields}", headers=headers
    )
    assert response.status_code == 200
    return (
        response.get_json()["data"].get("relationships", {}).get("backlinkedWorkItems")
    )


def test_created_link_is_listed_on_its_source(client, pat_headers, pair, fresh):
    source, target = pair
    created = link(client, pat_headers, source, target)
    assert created.status_code == 201, created.get_data(as_text=True)
    link_id = f"{PROJECT}/{source}/relates_to/{PROJECT}/{target}"
    assert created.get_json()["data"][0]["id"] == link_id

    payload = outgoing(client, pat_headers, source)
    assert payload["meta"]["totalCount"] == 1
    listed = payload["data"][0]
    assert listed["id"] == link_id
    assert listed["attributes"]["role"] == "relates_to"
    assert listed["relationships"]["workItem"]["data"]["id"] == f"{PROJECT}/{target}"


def test_same_link_twice_is_a_conflict(client, pat_headers, pair, fresh):
    source, target = pair
    assert link(client, pat_headers, source, target).status_code == 201
    assert link(client, pat_headers, source, target).status_code == 409
    assert outgoing(client, pat_headers, source)["meta"]["totalCount"] == 1


def test_target_lists_the_link_as_backlink(client, pat_headers, pair, fresh):
    source, target = pair
    link(client, pat_headers, source, target)
    link_id = f"{PROJECT}/{source}/relates_to/{PROJECT}/{target}"
    expected = {
        "data": [{"type": "linkedworkitems", "id": link_id}],
        "meta": {"totalCount": 1},
    }
    assert backlinks(client, pat_headers, target) == expected
    assert backlinks(client, pat_headers, target, "backlinkedWorkItems") == expected
    assert backlinks(client, pat_headers, target, "title") is None
    assert backlinks(client, pat_headers, source)["data"] == []


def test_delete_a_list_of_links(client, pat_headers, pair, fresh):
    source, target = pair
    link(client, pat_headers, source, target)
    link_id = f"{PROJECT}/{source}/relates_to/{PROJECT}/{target}"
    response = client.delete(
        f"{WI_URL}/{source}/linkedworkitems",
        headers=pat_headers,
        json={"data": [{"type": "linkedworkitems", "id": link_id}]},
    )
    assert response.status_code == 204, response.get_data(as_text=True)
    assert outgoing(client, pat_headers, source)["meta"]["totalCount"] == 0
    assert backlinks(client, pat_headers, target)["data"] == []


def test_deleting_an_unknown_link_deletes_nothing(client, pat_headers, pair, fresh):
    source, target = pair
    link(client, pat_headers, source, target)
    response = client.delete(
        f"{WI_URL}/{source}/linkedworkitems",
        headers=pat_headers,
        json={
            "data": [
                {
                    "type": "linkedworkitems",
                    "id": f"{PROJECT}/{source}/relates_to/{PROJECT}/{target}",
                },
                {
                    "type": "linkedworkitems",
                    "id": f"{PROJECT}/{source}/parent/{PROJECT}/{target}",
                },
            ]
        },
    )
    assert response.status_code == 404
    assert outgoing(client, pat_headers, source)["meta"]["totalCount"] == 1


def test_there_is_no_backlinked_endpoint(client, pat_headers, pair):
    source, _ = pair
    response = client.get(f"{WI_URL}/{source}/backlinkedworkitems", headers=pat_headers)
    assert response.status_code == 404
