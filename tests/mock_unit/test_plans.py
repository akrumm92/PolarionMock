"""GET /projects/{p}/plans and /projects/{p}/plans/{planId}."""

import pytest

from .conftest import PROJECT, REST_PREFIX, assert_matches_schema

pytestmark = pytest.mark.mock

PLANS = f"{REST_PREFIX}/projects/{PROJECT}/plans"


def test_plans_list_instances_only(client, pat_headers):
    response = client.get(PLANS, headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("plansListGetResponse", payload)
    assert [p["id"] for p in payload["data"]] == [
        f"{PROJECT}/Release_1", f"{PROJECT}/Iteration_1"]
    assert payload["meta"]["totalCount"] == 2


def test_templates_are_listed_on_request(client, pat_headers):
    payload = client.get(f"{PLANS}?templates=true", headers=pat_headers).get_json()
    assert [p["attributes"]["id"] for p in payload["data"]] == ["release", "iteration"]
    assert all(p["attributes"]["isTemplate"] for p in payload["data"])


def test_plans_query_paging_and_fields(client, pat_headers):
    url = f"{PLANS}?query=name%3AIteration*&fields%5Bplans%5D=id%2Cname"
    payload = client.get(url, headers=pat_headers).get_json()
    assert [p["attributes"] for p in payload["data"]] == [
        {"id": "Iteration_1", "name": "Iteration 1"}]
    paged = client.get(f"{PLANS}?page%5Bsize%5D=1&page%5Bnumber%5D=1",
                       headers=pat_headers).get_json()
    assert len(paged["data"]) == 1 and "next" in paged["links"]


def test_plan_carries_the_dumped_work_items(client, pat_headers, fixture_dump):
    response = client.get(f"{PLANS}/Release_1", headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("plansSingleGetResponse", payload)
    items = payload["data"]["relationships"]["workItems"]
    expected = [w["id"] for w in fixture_dump["workitems"] if w["type"] != "heading"]
    assert sorted(i["id"].split("/")[1] for i in items["data"]) == sorted(expected)
    assert items["meta"]["totalCount"] == len(expected)
    rel = payload["data"]["relationships"]
    assert rel["template"]["data"]["id"] == f"{PROJECT}/release"


def test_iteration_names_its_parent(client, pat_headers):
    payload = client.get(f"{PLANS}/Iteration_1", headers=pat_headers).get_json()
    parent = payload["data"]["relationships"]["parent"]["data"]
    assert parent == {"type": "plans", "id": f"{PROJECT}/Release_1"}


def test_unknown_plan_is_404(client, pat_headers):
    response = client.get(f"{PLANS}/nope", headers=pat_headers)
    assert response.status_code == 404
    assert "plans with id 'VPATHAI/nope'" in response.get_json()["errors"][0]["detail"]
