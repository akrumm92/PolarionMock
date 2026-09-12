"""
Authentication (Polarion PAT) and header handling of the mock.

Production Polarion accepts a Personal Access Token as ``Bearer`` token and
answers ``Accept: application/json`` as well as ``Accept: */*``. The mock
must do the same so a workflow needs nothing but a different base URL.
"""

import os

import pytest

from src.mock.middleware.auth import generate_mock_token

from .conftest import REST_PREFIX, make_fake_pat

pytestmark = [pytest.mark.mock, pytest.mark.unit, pytest.mark.security]

URL = f"{REST_PREFIX}/projects/VPATHAI"


@pytest.fixture
def pat_mode(monkeypatch):
    monkeypatch.setenv("MOCK_AUTH_MODE", "pat")
    monkeypatch.setenv("DISABLE_AUTH", "false")
    monkeypatch.delenv("MOCK_PAT_CHECK_EXPIRY", raising=False)
    monkeypatch.delenv("MOCK_ACCEPTED_TOKENS", raising=False)
    monkeypatch.delenv("POLARION_PERSONAL_ACCESS_TOKEN", raising=False)


class TestPersonalAccessToken:
    def test_polarion_shaped_pat_is_accepted(self, client, pat_mode):
        response = client.get(URL, headers={"Authorization": f"Bearer {make_fake_pat()}", "Accept": "*/*"})
        assert response.status_code == 200

    def test_expired_pat_is_accepted_by_default(self, client, pat_mode):
        """Offline testing must not break when the customer PAT expires."""
        expired = make_fake_pat(expires_in=-3600)
        response = client.get(URL, headers={"Authorization": f"Bearer {expired}", "Accept": "*/*"})
        assert response.status_code == 200

    def test_expired_pat_is_rejected_when_expiry_check_is_on(self, client, pat_mode, monkeypatch):
        monkeypatch.setenv("MOCK_PAT_CHECK_EXPIRY", "true")
        expired = make_fake_pat(expires_in=-3600)
        response = client.get(URL, headers={"Authorization": f"Bearer {expired}", "Accept": "*/*"})
        assert response.status_code == 401
        assert response.get_json()["errors"][0]["detail"] == "Token has expired"

    def test_garbage_token_is_401(self, client, pat_mode):
        response = client.get(URL, headers={"Authorization": "Bearer not-a-token", "Accept": "*/*"})
        assert response.status_code == 401
        error = response.get_json()["errors"][0]
        assert error["status"] == "401" and error["title"] == "Unauthorized"

    def test_missing_header_is_401(self, client, pat_mode):
        response = client.get(URL, headers={"Accept": "*/*"})
        assert response.status_code == 401

    def test_basic_auth_is_401(self, client, pat_mode):
        response = client.get(URL, headers={"Authorization": "Basic abc", "Accept": "*/*"})
        assert response.status_code == 401

    def test_mock_jwt_still_works(self, client, app, pat_mode):
        with app.app_context():
            token = generate_mock_token("tester")
        response = client.get(URL, headers={"Authorization": f"Bearer {token}", "Accept": "*/*"})
        assert response.status_code == 200

    def test_allow_listed_opaque_token(self, client, pat_mode, monkeypatch):
        monkeypatch.setenv("MOCK_ACCEPTED_TOKENS", "alpha, beta")
        response = client.get(URL, headers={"Authorization": "Bearer beta", "Accept": "*/*"})
        assert response.status_code == 200

    def test_env_pat_is_allow_listed(self, client, pat_mode, monkeypatch):
        monkeypatch.setenv("POLARION_PERSONAL_ACCESS_TOKEN", "opaque-pat-value")
        response = client.get(URL, headers={"Authorization": "Bearer opaque-pat-value", "Accept": "*/*"})
        assert response.status_code == 200

    def test_strict_mode_rejects_polarion_pat(self, client, pat_mode, monkeypatch):
        monkeypatch.setenv("MOCK_AUTH_MODE", "strict")
        response = client.get(URL, headers={"Authorization": f"Bearer {make_fake_pat()}", "Accept": "*/*"})
        assert response.status_code == 401

    def test_disabled_mode_needs_no_token(self, client, pat_mode, monkeypatch):
        monkeypatch.setenv("MOCK_AUTH_MODE", "disabled")
        assert client.get(URL, headers={"Accept": "*/*"}).status_code == 200

    def test_health_needs_no_token(self, client, pat_mode):
        assert client.get("/health").status_code == 200


class TestAcceptHeader:
    @pytest.mark.parametrize("accept", ["*/*", "application/json", "application/vnd.api+json",
                                        "application/json, text/plain, */*", "application/json;q=0.9"])
    def test_json_capable_accept_headers_are_ok(self, client, pat_mode, accept):
        response = client.get(URL, headers={"Authorization": f"Bearer {make_fake_pat()}", "Accept": accept})
        assert response.status_code == 200, accept

    def test_no_accept_header_is_ok(self, client, pat_mode):
        response = client.get(URL, headers={"Authorization": f"Bearer {make_fake_pat()}"})
        assert response.status_code == 200

    @pytest.mark.parametrize("accept", ["text/html", "application/xml", "image/png"])
    def test_non_json_accept_is_406(self, client, pat_mode, accept):
        response = client.get(URL, headers={"Authorization": f"Bearer {make_fake_pat()}", "Accept": accept})
        assert response.status_code == 406
        assert response.get_json()["errors"][0]["status"] == "406"

    def test_post_without_json_content_type_is_415(self, client, pat_mode):
        response = client.post(f"{REST_PREFIX}/projects/VPATHAI/workitems",
                               data="x", headers={"Authorization": f"Bearer {make_fake_pat()}",
                                                  "Accept": "*/*", "Content-Type": "text/plain"})
        assert response.status_code == 415
