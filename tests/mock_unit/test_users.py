"""GET /users and /users/{userId} as Polarion REST v1 has them."""

import pytest

from .conftest import REST_PREFIX, assert_matches_schema

pytestmark = pytest.mark.mock


def test_users_are_listed_with_total_count(client, pat_headers):
    response = client.get(f"{REST_PREFIX}/users", headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("usersListGetResponse", payload)
    ids = [user["id"] for user in payload["data"]]
    assert "admin" in ids and payload["meta"]["totalCount"] == len(ids)
    assert all(user["type"] == "users" for user in payload["data"])


def test_users_are_paged(client, pat_headers):
    url = f"{REST_PREFIX}/users?page%5Bsize%5D=1&page%5Bnumber%5D=2"
    payload = client.get(url, headers=pat_headers).get_json()
    assert len(payload["data"]) == 1
    assert payload["meta"]["totalCount"] > 1
    assert "prev" in payload["links"] and "first" in payload["links"]


def test_users_query_and_sparse_fields(client, pat_headers):
    url = (f"{REST_PREFIX}/users?query=name%3AJohn*"
           "&fields%5Busers%5D=id%2Cname%2Cemail")
    payload = client.get(url, headers=pat_headers).get_json()
    assert [user["id"] for user in payload["data"]] == ["john.doe"]
    assert set(payload["data"][0]["attributes"]) == {"id", "name", "email"}


def test_unsupported_query_is_refused(client, pat_headers):
    url = f"{REST_PREFIX}/users?query=name%3AJohn%20OR%20name%3AJane"
    response = client.get(url, headers=pat_headers)
    assert response.status_code == 400


def test_single_user_and_unknown_user(client, pat_headers):
    payload = client.get(f"{REST_PREFIX}/users/jane.smith", headers=pat_headers).get_json()
    assert_matches_schema("usersSingleGetResponse", payload)
    assert payload["data"]["attributes"]["name"] == "Jane Smith"
    response = client.get(f"{REST_PREFIX}/users/nobody", headers=pat_headers)
    assert response.status_code == 404
    assert_matches_schema("errors", response.get_json())
