"""GET /projects/{p}/collections and /projects/{p}/collections/{collectionId}."""

import pytest

from .conftest import DOCUMENT_ID, PROJECT, REST_PREFIX, assert_matches_schema

pytestmark = pytest.mark.mock

COLLECTIONS = f"{REST_PREFIX}/projects/{PROJECT}/collections"


def test_collections_are_listed(client, pat_headers):
    response = client.get(COLLECTIONS, headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("collectionsListGetResponse", payload)
    assert [c["id"] for c in payload["data"]] == [f"{PROJECT}/baseline_1"]
    assert payload["meta"]["totalCount"] == 1


def test_collection_holds_the_dumped_document(client, pat_headers):
    response = client.get(f"{COLLECTIONS}/baseline_1", headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("collectionsSingleGetResponse", payload)
    documents = payload["data"]["relationships"]["documents"]
    assert documents["data"] == [{"type": "documents", "id": DOCUMENT_ID}]
    assert documents["meta"]["totalCount"] == 1
    assert payload["data"]["attributes"]["name"] == "Baseline 1"


def test_seeded_collections_of_other_projects(client, pat_headers):
    url = f"{REST_PREFIX}/projects/automotive/collections?query=name%3ASafety*"
    payload = client.get(url, headers=pat_headers).get_json()
    assert_matches_schema("collectionsListGetResponse", payload)
    assert [c["id"] for c in payload["data"]] == ["automotive/safety_critical"]


def test_sparse_fields_and_paging(client, pat_headers):
    url = f"{COLLECTIONS}?fields%5Bcollections%5D=id%2Cname&page%5Bsize%5D=1"
    payload = client.get(url, headers=pat_headers).get_json()
    assert payload["data"][0]["attributes"] == {"id": "baseline_1", "name": "Baseline 1"}
    assert "next" not in payload["links"]


@pytest.mark.parametrize("url, detail", [
    (f"{COLLECTIONS}/nope", "collections with id 'VPATHAI/nope'"),
    (f"{REST_PREFIX}/projects/NOPE/collections", "Project id NOPE does not exist."),
])
def test_unknown_collection_or_project_is_404(client, pat_headers, url, detail):
    response = client.get(url, headers=pat_headers)
    assert response.status_code == 404
    assert detail in response.get_json()["errors"][0]["detail"]
