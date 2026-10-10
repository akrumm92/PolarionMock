"""
``GET /projects/{projectId}/workitems/{workItemId}/relationships/{relationshipId}``
(``getWorkItemsRelationships``) as Polarion REST v1 has it: a to-many
relationship is paged with ``page[size]``/``page[number]`` and carries
``meta.totalCount``; a to-one relationship answers one identifier; an unknown
relationship is a 404 in the JSON:API ``errors`` shape. Backlinks are read here,
REST v1 has no ``.../backlinkedworkitems`` endpoint.
"""

import pytest

from .conftest import PROJECT, REST_PREFIX
from .test_workitem_links import fresh, link, pair  # noqa: F401

pytestmark = [pytest.mark.mock, pytest.mark.unit]

WI_URL = f"{REST_PREFIX}/projects/{PROJECT}/workitems"


def relationship(client, headers, wi, name, size=None, number=None):
    query = ""
    if size is not None:
        query = f"?page%5Bsize%5D={size}&page%5Bnumber%5D={number}"
    return client.get(f"{WI_URL}/{wi}/relationships/{name}{query}", headers=headers)


def link_id(source, target, role="relates_to"):
    return f"{PROJECT}/{source}/{role}/{PROJECT}/{target}"


def test_backlinked_work_items_lists_links_pointing_here(
    client, pat_headers, pair, fresh  # noqa: F811
):
    source, target = pair
    assert link(client, pat_headers, source, target).status_code == 201
    response = relationship(client, pat_headers, target, "backlinkedWorkItems", 100, 1)
    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body["data"] == [
        {"type": "linkedworkitems", "id": link_id(source, target)}
    ]
    assert body["meta"]["totalCount"] == 1


def test_linked_work_items_lists_links_stored_here(
    client, pat_headers, pair, fresh  # noqa: F811
):
    source, target = pair
    link(client, pat_headers, source, target)
    body = relationship(client, pat_headers, source, "linkedWorkItems").get_json()
    assert body["data"] == [
        {"type": "linkedworkitems", "id": link_id(source, target)}
    ]
    assert body["meta"]["totalCount"] == 1
    empty = relationship(client, pat_headers, target, "linkedWorkItems").get_json()
    assert empty["data"] == [] and empty["meta"]["totalCount"] == 0


def test_to_many_relationship_is_paged(
    client, pat_headers, fixture_dump, fresh  # noqa: F811
):
    items = [p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"]]
    target, sources = items[0], items[1:4]
    for source in sources:
        assert link(client, pat_headers, source, target).status_code == 201
    first = relationship(client, pat_headers, target, "backlinkedWorkItems", 2, 1)
    second = relationship(client, pat_headers, target, "backlinkedWorkItems", 2, 2)
    first, second = first.get_json(), second.get_json()
    assert first["meta"]["totalCount"] == 3 and second["meta"]["totalCount"] == 3
    assert len(first["data"]) == 2 and len(second["data"]) == 1
    ids = {r["id"] for r in first["data"] + second["data"]}
    assert ids == {link_id(source, target) for source in sources}
    assert "next" in first["links"] and "next" not in second["links"]


def test_to_one_relationship_answers_one_identifier(client, pat_headers, pair):
    source, _ = pair
    item = client.get(f"{WI_URL}/{source}", headers=pat_headers).get_json()["data"]
    expected = item["relationships"]["project"]["data"]
    body = relationship(client, pat_headers, source, "project").get_json()
    assert body["data"] == expected
    assert "meta" not in body


def test_unknown_relationship_is_a_json_api_404(client, pat_headers, pair):
    source, _ = pair
    response = relationship(client, pat_headers, source, "noSuchRelationship")
    assert response.status_code == 404
    error = response.get_json()["errors"][0]
    assert error["status"] == "404" and error["title"] == "Not Found"
    assert "noSuchRelationship" in error["detail"]


def test_unknown_work_item_is_a_404(client, pat_headers):
    response = relationship(client, pat_headers, "NO-SUCH-1", "backlinkedWorkItems")
    assert response.status_code == 404
    assert response.get_json()["errors"][0]["status"] == "404"
