"""
Contract of the mock for the customer workflow
``lexion_fsm_polarion_requirements_read`` (CQ-WKP-C-CLAASNEW-LFP-04).

The workflow's fetch stage issues exactly two kinds of GET requests:

1. ``.../spaces/{space}/documents/{name}/parts?fields[document_parts]=@all
   &page[size]=100&page[number]=N`` - paginated over ``links.next``,
   completeness checked against ``meta.totalCount``.
2. ``.../workitems/{id}?fields[workitems]=id,title,type,outlineNumber,
   description,status`` - one per referenced work item.

The mock serves the document exported from production (fixture dump). These
tests replay the sequence and require the result to be IDENTICAL to the
export; then they pin the JSON:API details the script depends on.
"""

import collections
import re

import pytest

from .conftest import (
    DOCUMENT_ID,
    PROJECT,
    REST_PREFIX,
    parts_url,
    replay_fetch,
    workitem_url,
)

pytestmark = [pytest.mark.mock, pytest.mark.unit]


class TestFetchSequenceMatchesExport:
    """The raw dump assembled from the mock equals the production export."""

    def test_parts_and_workitems_identical_to_export(self, client, pat_headers, fixture_dump):
        result = replay_fetch(client, pat_headers)

        assert result["pages"] == 3, "218 parts at page size 100 -> 3 pages"
        assert result["reported"] == fixture_dump["document"]["part_count_reported"] == 218
        assert len(result["parts"]) == result["reported"], "fetched == reported (completeness guard)"
        assert result["parts"] == fixture_dump["parts"]
        assert result["workitems"] == fixture_dump["workitems"]
        assert len(result["workitems"]) == fixture_dump["document"]["work_item_count"] == 158

    def test_requirement_filter_of_the_etl_scenario(self, client, pat_headers, fixture_dump):
        """The JQ_ONLY scenario keeps systemrequirement + componentrequirement."""
        result = replay_fetch(client, pat_headers)
        by_type = collections.Counter(w["type"] for w in result["workitems"])
        assert by_type["systemrequirement"] == 10
        assert by_type["componentrequirement"] == 19
        requirements = [w for w in result["workitems"]
                        if w["type"] in ("systemrequirement", "componentrequirement")]
        assert len(requirements) == 29
        assert len({w["id"] for w in requirements}) == 29, "ids pairwise distinct"
        assert all(w["outlineNumber"] for w in requirements), "every requirement has an outline number"
        assert any(w["description_html"] for w in requirements)
        # the deliberate non-requirement of the document must be present but filtered
        userstories = [w for w in result["workitems"] if w["type"] == "userstory"]
        assert len(userstories) == 1 and "ZZ PROOF" in userstories[0]["title"]


class TestDocumentPartsEndpoint:
    """JSON:API details of GET .../parts the fetch script relies on."""

    def test_first_page_shape(self, client, pat_headers):
        payload = client.get(parts_url(1), headers=pat_headers).get_json()

        assert set(payload) == {"links", "data", "meta"}
        assert payload["meta"] == {"totalCount": 218}
        assert len(payload["data"]) == 100
        links = payload["links"]
        assert set(links) == {"self", "first", "next", "last"}, "no prev on page 1"
        assert "page%5Bnumber%5D=2" in links["next"]
        assert "page%5Bnumber%5D=3" in links["last"]
        assert "fields%5Bdocument_parts%5D=%40all" in links["next"], "query is kept and encoded like Polarion"
        assert links["next"].startswith("http"), "absolute URLs"
        assert "/spaces/System%20Layer/documents/Technical_Specification-API_TEST/parts" in links["self"]

        first = payload["data"][0]
        assert first["type"] == "document_parts"
        assert first["id"] == f"{DOCUMENT_ID}/heading_VPAT-11137"
        assert first["attributes"]["id"] == "heading_VPAT-11137"
        assert first["attributes"]["type"] == "heading"
        assert first["attributes"]["content"].startswith("<h1 ")
        assert first["relationships"]["workItem"]["data"] == {"type": "workitems", "id": "VPATHAI/VPAT-11137"}
        assert first["links"]["self"].endswith("/parts/heading_VPAT-11137")

    def test_last_page_has_no_next(self, client, pat_headers):
        payload = client.get(parts_url(3), headers=pat_headers).get_json()
        assert len(payload["data"]) == 18
        assert "next" not in payload["links"]
        assert "prev" in payload["links"] and "page%5Bnumber%5D=2" in payload["links"]["prev"]
        assert payload["meta"]["totalCount"] == 218

    def test_page_beyond_last_is_empty_but_reports_total(self, client, pat_headers):
        payload = client.get(parts_url(99), headers=pat_headers).get_json()
        assert payload["data"] == []
        assert payload["meta"]["totalCount"] == 218
        assert "next" not in payload["links"]

    def test_page_size_is_capped_at_100(self, client, pat_headers):
        payload = client.get(parts_url(1, page_size=1000), headers=pat_headers).get_json()
        assert len(payload["data"]) == 100

    def test_parts_without_workitem_have_no_relationship(self, client, pat_headers):
        payload = client.get(parts_url(1), headers=pat_headers).get_json()
        text_parts = [p for p in payload["data"] if p["attributes"]["type"] == "normal"]
        assert text_parts, "the document has plain text parts"
        assert all("relationships" not in p for p in text_parts)

    def test_part_types_of_the_export_are_served(self, client, pat_headers, fixture_dump):
        types = collections.Counter()
        for page in (1, 2, 3):
            for part in client.get(parts_url(page), headers=pat_headers).get_json()["data"]:
                types[part["attributes"]["type"]] += 1
        expected = collections.Counter(p["part_type"] for p in fixture_dump["parts"])
        assert types == expected  # workitem, heading, normal, pagebreak, table, toc, tof, wikiblock

    def test_sparse_fieldsets(self, client, pat_headers):
        payload = client.get(parts_url(1, fields="id,type"), headers=pat_headers).get_json()
        assert set(payload["data"][0]["attributes"]) == {"id", "type"}

    def test_include_workitem(self, client, pat_headers):
        url = parts_url(1) + "&include=workItem"
        payload = client.get(url, headers=pat_headers).get_json()
        included = {item["id"]: item for item in payload.get("included", [])}
        assert "VPATHAI/VPAT-11137" in included
        assert included["VPATHAI/VPAT-11137"]["type"] == "workitems"
        assert included["VPATHAI/VPAT-11137"]["attributes"]["title"] == "Technical Specification - API_TEST"

    def test_single_part(self, client, pat_headers):
        url = f"{REST_PREFIX}/projects/VPATHAI/spaces/System%20Layer/documents/Technical_Specification-API_TEST/parts/heading_VPAT-11137"
        payload = client.get(url, headers=pat_headers).get_json()
        assert payload["data"]["attributes"]["id"] == "heading_VPAT-11137"

    def test_unknown_document_is_404(self, client, pat_headers):
        url = f"{REST_PREFIX}/projects/VPATHAI/spaces/System%20Layer/documents/Nope/parts"
        response = client.get(url, headers=pat_headers)
        assert response.status_code == 404
        assert response.get_json()["errors"][0]["status"] == "404"

    def test_unknown_project_is_404_with_polarion_message(self, client, pat_headers):
        url = f"{REST_PREFIX}/projects/NOPE/spaces/System%20Layer/documents/Technical_Specification-API_TEST/parts"
        response = client.get(url, headers=pat_headers)
        assert response.status_code == 404
        assert response.get_json()["errors"][0]["detail"] == "Project id NOPE does not exist."


class TestWorkItemEndpoint:
    """JSON:API details of GET .../workitems/{id} the fetch script relies on."""

    def test_requested_fields_only(self, client, pat_headers):
        payload = client.get(workitem_url("VPAT-11134"), headers=pat_headers).get_json()
        attributes = payload["data"]["attributes"]
        assert set(attributes) == {"id", "title", "type", "outlineNumber", "description", "status"}
        assert attributes["id"] == "VPAT-11134"
        assert attributes["type"] == "systemrequirement"
        assert attributes["outlineNumber"] == "2-1"
        assert attributes["status"] == "draft"
        assert attributes["description"]["type"] == "text/html"
        assert attributes["description"]["value"].startswith("<p><p>Das System kennt")
        assert payload["data"]["id"] == "VPATHAI/VPAT-11134"
        assert payload["links"]["self"].startswith("http")
        assert payload["data"]["links"]["self"].startswith("http")

    def test_heading_without_description_and_outline(self, client, pat_headers):
        """The document title heading has no outlineNumber and no description."""
        payload = client.get(workitem_url("VPAT-11137"), headers=pat_headers).get_json()
        attributes = payload["data"]["attributes"]
        assert attributes["type"] == "heading"
        assert "description" not in attributes
        assert "outlineNumber" not in attributes

    def test_all_fields(self, client, pat_headers):
        payload = client.get(workitem_url("VPAT-11134", fields="@all"), headers=pat_headers).get_json()
        attributes = payload["data"]["attributes"]
        assert {"id", "title", "type", "status", "created", "updated"} <= set(attributes)
        assert payload["data"]["relationships"]["module"]["data"]["id"] == DOCUMENT_ID

    def test_include_module(self, client, pat_headers):
        payload = client.get(workitem_url("VPAT-11134") + "&include=module", headers=pat_headers).get_json()
        assert payload["included"][0]["type"] == "documents"
        assert payload["included"][0]["id"] == DOCUMENT_ID

    def test_unknown_workitem_is_404(self, client, pat_headers):
        response = client.get(workitem_url("VPAT-1"), headers=pat_headers)
        assert response.status_code == 404

    def test_umlauts_are_not_escaped(self, client, pat_headers, fixture_dump):
        """Polarion returns UTF-8 as-is; the export carries such characters."""
        with_non_ascii = next(w for w in fixture_dump["workitems"]
                              if re.search(r"[^\x00-\x7f]", w["description_html"]))
        response = client.get(workitem_url(with_non_ascii["id"]), headers=pat_headers)
        body = response.get_data(as_text=True)
        assert "\\u" not in body.split('"value"', 1)[1][:2000]
        assert response.get_json()["data"]["attributes"]["description"]["value"] == with_non_ascii["description_html"]


class TestProjectAndDocumentOfTheExport:
    def test_project_exists_with_tracker_prefix(self, client, pat_headers):
        payload = client.get(f"{REST_PREFIX}/projects/{PROJECT}", headers=pat_headers).get_json()
        assert payload["data"]["id"] == PROJECT
        assert payload["data"]["attributes"]["trackerPrefix"] == "VPAT"

    def test_document_exists(self, client, pat_headers):
        url = f"{REST_PREFIX}/projects/VPATHAI/spaces/System%20Layer/documents/Technical_Specification-API_TEST"
        payload = client.get(url, headers=pat_headers).get_json()
        assert payload["data"]["id"] == DOCUMENT_ID
        assert payload["data"]["attributes"]["name"] == "Technical_Specification-API_TEST"

    def test_workitems_of_project_are_listed_with_module(self, client, pat_headers):
        url = f"{REST_PREFIX}/projects/VPATHAI/workitems?page%5Bsize%5D=100&page%5Bnumber%5D=2"
        payload = client.get(url, headers=pat_headers).get_json()
        assert payload["meta"]["totalCount"] == 158
        assert len(payload["data"]) == 58
        assert all(item["relationships"]["module"]["data"]["id"] == DOCUMENT_ID for item in payload["data"])
