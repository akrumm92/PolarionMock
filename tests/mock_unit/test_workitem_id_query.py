"""
Lucene ``id:`` in a work item query: ``id:X``, ``id:(X Y ...)`` and the
project-qualified ``id:"PROJ/X"`` return exactly the named work items.
"""

from urllib.parse import quote

import pytest

from .conftest import PROJECT, REST_PREFIX

pytestmark = [pytest.mark.mock, pytest.mark.unit]


def query(client, headers, lucene, path=f"/projects/{PROJECT}/workitems", size=100):
    response = client.get(
        f"{REST_PREFIX}{path}?query={quote(lucene, safe='')}"
        f"&fields%5Bworkitems%5D=title,type&page%5Bsize%5D={size}",
        headers=headers,
    )
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    return [item["id"] for item in payload["data"]], payload["meta"]["totalCount"]


@pytest.fixture(scope="module")
def dump_ids(fixture_dump):
    return [p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"]]


def test_single_id(client, pat_headers, dump_ids):
    ids, total = query(client, pat_headers, f"id:{dump_ids[5]}")
    assert ids == [f"{PROJECT}/{dump_ids[5]}"] and total == 1


def test_id_list(client, pat_headers, dump_ids):
    wanted = [dump_ids[0], dump_ids[-1], dump_ids[70]]
    ids, total = query(client, pat_headers, f"id:({' '.join(wanted)})")
    assert sorted(ids) == sorted(f"{PROJECT}/{w}" for w in wanted) and total == 3


def test_project_qualified_id(client, pat_headers, dump_ids):
    ids, _ = query(client, pat_headers, f'id:"{PROJECT}/{dump_ids[3]}"')
    assert ids == [f"{PROJECT}/{dump_ids[3]}"]


def test_second_batch_of_a_long_list_returns_its_own_items(
    client, pat_headers, dump_ids
):
    second = dump_ids[100:150]
    ids, total = query(client, pat_headers, f"id:({' '.join(second)})")
    assert sorted(ids) == sorted(f"{PROJECT}/{w}" for w in second)
    assert total == len(second)


def test_id_combined_with_type(client, pat_headers, fixture_dump):
    heading = next(
        p["workitem_id"] for p in fixture_dump["parts"] if p["part_type"] == "heading"
    )
    other = next(
        p["workitem_id"] for p in fixture_dump["parts"] if p["part_type"] == "workitem"
    )
    ids, _ = query(client, pat_headers, f"id:({heading} {other}) AND type:heading")
    assert ids == [f"{PROJECT}/{heading}"]


def test_unknown_id_matches_nothing(client, pat_headers):
    assert query(client, pat_headers, "id:VPAT-0") == ([], 0)


def test_module_query_is_not_read_as_id(client, pat_headers, dump_ids):
    document = f"{PROJECT}/System Layer/Technical_Specification-API_TEST"
    ids, total = query(client, pat_headers, f"module.id:{document}", size=100)
    assert total == len(set(dump_ids))


def test_id_query_across_projects(client, pat_headers, dump_ids):
    ids, total = query(client, pat_headers, f"id:{dump_ids[1]}", path="/all/workitems")
    assert ids == [f"{PROJECT}/{dump_ids[1]}"] and total == 1
