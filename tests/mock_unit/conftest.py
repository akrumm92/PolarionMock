"""
Fixtures for the in-process mock tests (Flask test client, no live server).

These tests exercise the mock exactly the way the customer workflow
``lexion_fsm_polarion_requirements_read`` does: Polarion PAT in the
``Authorization`` header, ``Accept: application/json``, paginated document
parts with ``fields[document_parts]=@all`` and single work items with
``fields[workitems]=id,title,type,outlineNumber,description,status``.
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_DUMP = ROOT / "src" / "mock" / "mock_data" / "polarion_dumps" / \
    "VPATHAI_System-Layer_Technical_Specification-API_TEST.json"
OPENAPI_SPEC = ROOT / "Input" / "api" / "polarionrest.json"

# Coordinates of the exported document (= the workflow overlay values)
PROJECT = "VPATHAI"
SPACE = "System Layer"
DOCUMENT = "Technical_Specification-API_TEST"
DOCUMENT_ID = f"{PROJECT}/{SPACE}/{DOCUMENT}"

# Field list the customer fetch script requests for work items
WORK_ITEM_FIELDS = "id,title,type,outlineNumber,description,status"
REST_PREFIX = "/polarion/rest/v1"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_fake_pat(subject: str = "E017093", expires_in: int = 3600) -> str:
    """A token shaped like a Polarion PAT (RS256 JWT) with a bogus signature.

    The mock cannot verify Polarion's RSA signature, so any structurally valid
    JWT is accepted in ``pat`` mode. No real credential is used in the tests.
    """
    header = {"kid": "test-kid", "typ": "JWT", "alg": "RS256"}
    now = int(time.time())
    payload = {"sub": subject, "id": "0123-4567", "exp": now + expires_in, "iat": now}
    return ".".join([
        _b64url(json.dumps(header, separators=(",", ":")).encode()),
        _b64url(json.dumps(payload, separators=(",", ":")).encode()),
        _b64url(b"not-a-real-signature"),
    ])


@pytest.fixture(scope="session")
def fixture_dump() -> dict:
    with open(FIXTURE_DUMP, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def app():
    """The Flask app in PAT mode (the mode a workflow run needs)."""
    os.environ["MOCK_AUTH_MODE"] = "pat"
    os.environ["DISABLE_AUTH"] = "false"
    os.environ.pop("MOCK_PAT_CHECK_EXPIRY", None)
    os.environ.setdefault("LOG_FORMAT", "text")
    from src.mock.app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def fake_pat() -> str:
    return make_fake_pat()


@pytest.fixture
def pat_headers(fake_pat) -> Dict[str, str]:
    """Headers exactly as the customer fetch script sends them."""
    return {"Authorization": f"Bearer {fake_pat}", "Accept": "application/json"}


def parts_url(page: int, page_size: int = 100, fields: str = "@all") -> str:
    """URL built exactly like ``polarion_read.fetch_parts`` builds it."""
    space_encoded = quote(SPACE, safe="")
    fields_key = quote("fields[document_parts]", safe="")
    return (f"{REST_PREFIX}/projects/{PROJECT}/spaces/{space_encoded}"
            f"/documents/{DOCUMENT}/parts?{fields_key}={quote(fields, safe='')}"
            f"&page%5Bsize%5D={page_size}&page%5Bnumber%5D={page}")


def workitem_url(workitem_id: str, fields: str = WORK_ITEM_FIELDS) -> str:
    """URL built exactly like ``polarion_read.fetch_work_items`` builds it."""
    fields_key = quote("fields[workitems]", safe="")
    return f"{REST_PREFIX}/projects/{PROJECT}/workitems/{workitem_id}?{fields_key}={quote(fields, safe='')}"


def replay_fetch(client, headers) -> dict:
    """Re-implementation of the fetch script's read sequence (GET only).

    Returns ``{"parts": [...], "workitems": [...], "reported": int, "pages": int}``
    with the same per-item shape the script writes into the raw dump.
    """
    parts, reported, page, pages = [], None, 1, 0
    while True:
        response = client.get(parts_url(page), headers=headers)
        assert response.status_code == 200, response.get_data(as_text=True)[:400]
        payload = response.get_json()
        pages += 1
        if reported is None:
            reported = (payload.get("meta") or {}).get("totalCount")
        for item in payload.get("data", []):
            attributes = item.get("attributes") or {}
            reference = ((item.get("relationships") or {}).get("workItem") or {}).get("data")
            parts.append({
                "part_id": attributes.get("id"),
                "part_type": attributes.get("type"),
                "content_html": attributes.get("content") or "",
                "workitem_id": str(reference["id"]).rsplit("/", 1)[-1] if reference else None,
            })
        if not (payload.get("links") or {}).get("next"):
            break
        page += 1

    referenced = sorted({p["workitem_id"] for p in parts if p["workitem_id"]})
    workitems = []
    for workitem_id in referenced:
        response = client.get(workitem_url(workitem_id), headers=headers)
        assert response.status_code == 200, (workitem_id, response.status_code)
        attributes = (response.get_json().get("data") or {}).get("attributes") or {}
        description = attributes.get("description")
        workitems.append({
            "id": workitem_id,
            "title": attributes.get("title") or "",
            "type": attributes.get("type") or "",
            "outlineNumber": attributes.get("outlineNumber"),
            "status": attributes.get("status") or "",
            "description_html": (
                (description or {}).get("value") or "" if isinstance(description, dict)
                else (description or "")
            ),
        })
    return {"parts": parts, "workitems": workitems, "reported": reported, "pages": pages}
