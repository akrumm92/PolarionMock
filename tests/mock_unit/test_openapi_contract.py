"""
The mock's responses for the workflow endpoints validate against the
Polarion REST API OpenAPI specification in ``Input/api/polarionrest.json``
(the spec extracted from the customer's Polarion instance).

To validate against a newer Polarion release, replace that file with the
``/polarion/rest/v1/openapi.json`` (or Swagger) export of the new server.
"""

import json

import jsonschema
import pytest

from .conftest import OPENAPI_SPEC, REST_PREFIX, parts_url, workitem_url

pytestmark = [pytest.mark.mock, pytest.mark.contract]


@pytest.fixture(scope="module")
def spec() -> dict:
    if not OPENAPI_SPEC.is_file():
        pytest.skip(f"OpenAPI spec not found: {OPENAPI_SPEC}")
    with open(OPENAPI_SPEC, encoding="utf-8") as handle:
        return json.load(handle)


def _validate(spec: dict, schema_name: str, instance: dict) -> None:
    schema = {"$ref": f"#/components/schemas/{schema_name}"}
    resolver = jsonschema.RefResolver.from_schema(spec)
    validator = jsonschema.Draft7Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors[:10])


def test_spec_describes_the_workflow_endpoints(spec):
    paths = spec["paths"]
    assert "get" in paths["/projects/{projectId}/spaces/{spaceId}/documents/{documentName}/parts"]
    assert "get" in paths["/projects/{projectId}/workitems/{workItemId}"]


def test_document_parts_list_response_matches_schema(spec, client, pat_headers):
    payload = client.get(parts_url(1), headers=pat_headers).get_json()
    _validate(spec, "document_partsListGetResponse", payload)


def test_document_parts_last_page_matches_schema(spec, client, pat_headers):
    payload = client.get(parts_url(3), headers=pat_headers).get_json()
    _validate(spec, "document_partsListGetResponse", payload)


def test_document_part_single_response_matches_schema(spec, client, pat_headers):
    url = f"{REST_PREFIX}/projects/VPATHAI/spaces/System%20Layer/documents/Technical_Specification-API_TEST/parts/heading_VPAT-11137"
    payload = client.get(url, headers=pat_headers).get_json()
    _validate(spec, "document_partsSingleGetResponse", payload)


@pytest.mark.parametrize("fields", ["id,title,type,outlineNumber,description,status", "@all"])
def test_workitem_single_response_matches_schema(spec, client, pat_headers, fields):
    payload = client.get(workitem_url("VPAT-11134", fields=fields), headers=pat_headers).get_json()
    _validate(spec, "workitemsSingleGetResponse", payload)


def test_workitem_list_response_matches_schema(spec, client, pat_headers):
    url = f"{REST_PREFIX}/projects/VPATHAI/workitems?page%5Bsize%5D=100&page%5Bnumber%5D=1"
    payload = client.get(url, headers=pat_headers).get_json()
    _validate(spec, "workitemsListGetResponse", payload)


def test_error_response_matches_schema(spec, client, pat_headers):
    response = client.get(workitem_url("VPAT-1"), headers=pat_headers)
    assert response.status_code == 404
    _validate(spec, "errors", response.get_json())
