"""
Work item comments as Polarion REST v1 has them: list, create (a reply names
its parentComment), read one, and set ``resolved``.
"""

import pytest

from .conftest import PROJECT, REST_PREFIX

pytestmark = [pytest.mark.mock, pytest.mark.unit]

WI_URL = f"{REST_PREFIX}/projects/{PROJECT}/workitems"
KIND = "workitem_comments"


@pytest.fixture
def fresh(client, pat_headers):
    client.post("/mock/admin/reset", headers=pat_headers)
    yield
    client.post("/mock/admin/reset", headers=pat_headers)


@pytest.fixture
def item(fixture_dump):
    return next(p["workitem_id"] for p in fixture_dump["parts"] if p["workitem_id"])


def comment(client, headers, item, text, parent=None):
    resource = {
        "type": KIND,
        "attributes": {"text": {"type": "text/html", "value": text}},
    }
    if parent:
        resource["relationships"] = {
            "parentComment": {"data": {"type": KIND, "id": parent}}
        }
    return client.post(
        f"{WI_URL}/{item}/comments", headers=headers, json={"data": [resource]}
    )


def listed(client, headers, item):
    response = client.get(
        f"{WI_URL}/{item}/comments?fields%5Bworkitem_comments%5D=%40all"
        "&page%5Bsize%5D=100&page%5Bnumber%5D=1",
        headers=headers,
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()


def test_no_comments_is_an_empty_list(client, pat_headers, item, fresh):
    payload = listed(client, pat_headers, item)
    assert payload["data"] == [] and payload["meta"]["totalCount"] == 0


def test_created_comment_is_listed(client, pat_headers, item, fresh):
    created = comment(client, pat_headers, item, "<p>Please check the limit.</p>")
    assert created.status_code == 201, created.get_data(as_text=True)
    new = created.get_json()["data"][0]
    assert new["type"] == KIND and new["id"] == f"{PROJECT}/{item}/1"
    assert new["links"]["self"].endswith(
        f"/projects/{PROJECT}/workitems/{item}/comments/1"
    )

    payload = listed(client, pat_headers, item)
    assert payload["meta"]["totalCount"] == 1
    first = payload["data"][0]
    assert first["id"] == f"{PROJECT}/{item}/1"
    assert first["attributes"]["id"] == "1"
    assert first["attributes"]["text"] == {
        "type": "text/html",
        "value": "<p>Please check the limit.</p>",
    }
    assert first["attributes"]["resolved"] is False
    assert first["relationships"]["author"]["data"]["type"] == "users"
    assert "parentComment" not in first["relationships"]


def test_reply_names_its_parent(client, pat_headers, item, fresh):
    comment(client, pat_headers, item, "<p>Question</p>")
    reply = comment(
        client, pat_headers, item, "<p>Answer</p>", parent=f"{PROJECT}/{item}/1"
    )
    assert reply.status_code == 201, reply.get_data(as_text=True)
    rows = {row["id"]: row for row in listed(client, pat_headers, item)["data"]}
    answer = rows[f"{PROJECT}/{item}/2"]
    assert answer["relationships"]["parentComment"]["data"] == {
        "type": KIND,
        "id": f"{PROJECT}/{item}/1",
    }
    question = rows[f"{PROJECT}/{item}/1"]
    assert question["relationships"]["childComments"]["data"] == [
        {"type": KIND, "id": f"{PROJECT}/{item}/2"}
    ]


def test_reply_to_unknown_comment_is_refused(client, pat_headers, item, fresh):
    response = comment(
        client, pat_headers, item, "<p>x</p>", parent=f"{PROJECT}/{item}/7"
    )
    assert response.status_code == 404
    assert listed(client, pat_headers, item)["meta"]["totalCount"] == 0


def test_comment_without_text_is_refused(client, pat_headers, item, fresh):
    response = client.post(
        f"{WI_URL}/{item}/comments",
        headers=pat_headers,
        json={"data": [{"type": KIND, "attributes": {}}]},
    )
    assert response.status_code == 400


def test_resolve_a_comment(client, pat_headers, item, fresh):
    comment(client, pat_headers, item, "<p>Done?</p>")
    url = f"{WI_URL}/{item}/comments/1"
    response = client.patch(
        url,
        headers=pat_headers,
        json={
            "data": {
                "type": KIND,
                "id": f"{PROJECT}/{item}/1",
                "attributes": {"resolved": True},
            }
        },
    )
    assert response.status_code == 204, response.get_data(as_text=True)
    one = client.get(url, headers=pat_headers)
    assert one.status_code == 200
    assert one.get_json()["data"]["attributes"]["resolved"] is True


def test_comments_of_an_unknown_work_item_are_404(client, pat_headers):
    assert (
        client.get(f"{WI_URL}/VPAT-0/comments", headers=pat_headers).status_code == 404
    )
