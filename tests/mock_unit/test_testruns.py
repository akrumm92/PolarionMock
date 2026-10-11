"""Test runs, their records and a test case's steps."""

import pytest

from .conftest import DOCUMENT, DOCUMENT_ID, PROJECT, REST_PREFIX, assert_matches_schema

pytestmark = pytest.mark.mock

RUNS = f"{REST_PREFIX}/projects/{PROJECT}/testruns"
AUTO = f"{REST_PREFIX}/projects/automotive"


def test_runs_list_instances_only(client, pat_headers):
    response = client.get(RUNS, headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("testrunsListGetResponse", payload)
    assert [r["id"] for r in payload["data"]] == [f"{PROJECT}/TestRun_1"]
    assert payload["meta"]["totalCount"] == 1
    templates = client.get(f"{RUNS}?templates=true", headers=pat_headers).get_json()
    assert [r["attributes"]["id"] for r in templates["data"]] == ["manual"]


def test_runs_query_and_fields(client, pat_headers):
    url = f"{RUNS}?query=status%3Aopen&fields%5Btestruns%5D=id%2Cstatus"
    payload = client.get(url, headers=pat_headers).get_json()
    assert [r["attributes"] for r in payload["data"]] == [
        {"id": "TestRun_1", "status": "open"}]
    none = client.get(f"{RUNS}?query=status%3Adone", headers=pat_headers).get_json()
    assert none["data"] == [] and none["meta"]["totalCount"] == 0


def test_run_of_the_dumped_document(client, pat_headers):
    response = client.get(f"{RUNS}/TestRun_1", headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("testrunsSingleGetResponse", payload)
    data = payload["data"]
    assert data["attributes"]["title"] == f"Test of {DOCUMENT}"
    assert data["relationships"]["document"]["data"]["id"] == DOCUMENT_ID
    records = client.get(f"{RUNS}/TestRun_1/testrecords", headers=pat_headers)
    assert records.status_code == 200
    assert_matches_schema("testrecordsListGetResponse", records.get_json())
    assert records.get_json()["meta"]["totalCount"] == 0   # the dump has no test cases


def test_records_of_a_run_with_a_test_case(client, pat_headers):
    payload = client.get(f"{AUTO}/testruns/TestRun_1/testrecords",
                         headers=pat_headers).get_json()
    assert_matches_schema("testrecordsListGetResponse", payload)
    record = payload["data"][0]
    assert record["id"] == "automotive/TestRun_1/automotive/AUTO-2/0"
    assert record["attributes"]["result"] == "passed"
    assert record["relationships"]["testCase"]["data"]["id"] == "automotive/AUTO-2"
    url = f"{AUTO}/testruns/TestRun_1/testrecords?testResultId=failed"
    assert client.get(url, headers=pat_headers).get_json()["data"] == []


def test_steps_of_a_test_case(client, pat_headers):
    response = client.get(f"{AUTO}/workitems/AUTO-2/teststeps", headers=pat_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert_matches_schema("teststepsListGetResponse", payload)
    assert payload["meta"]["totalCount"] == 2
    first = payload["data"][0]
    assert first["id"] == "automotive/AUTO-2/1"
    assert first["attributes"]["keys"] == ["step", "expectedResult"]
    assert first["attributes"]["values"][0]["type"] == "text/html"


def test_item_without_steps_answers_an_empty_list(client, pat_headers):
    url = f"{REST_PREFIX}/projects/{PROJECT}/workitems/VPAT-11134/teststeps"
    payload = client.get(url, headers=pat_headers).get_json()
    assert payload["data"] == [] and payload["meta"]["totalCount"] == 0


@pytest.mark.parametrize("url, detail", [
    (f"{RUNS}/nope", "testruns with id 'VPATHAI/nope'"),
    (f"{RUNS}/nope/testrecords", "testruns with id 'VPATHAI/nope'"),
    (f"{REST_PREFIX}/projects/{PROJECT}/workitems/VPAT-1/teststeps", "VPATHAI/VPAT-1'"),
])
def test_unknown_resources_are_404(client, pat_headers, url, detail):
    response = client.get(url, headers=pat_headers)
    assert response.status_code == 404
    assert detail in response.get_json()["errors"][0]["detail"]
