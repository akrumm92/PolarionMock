"""
End-to-end: the REAL customer fetch script against a LIVE mock server.

``fetch_polarion_document.py`` (customer capsule, project ground_guidance) is
the first stage of the workflow ``lexion_fsm_polarion_requirements_read``.
It is run here unchanged, as a subprocess, with the base URL pointing at a
mock server started in a background thread. Its raw dump must equal the
production export bundled with the mock (apart from ``base_url`` and
``fetched_at``).

The script path defaults to the customer capsule on this machine and can be
overridden with ``VPATH_FETCH_SCRIPT``. The test is skipped when the script
is not available (e.g. on CI).
"""

import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from .conftest import DOCUMENT, PROJECT, SPACE, make_fake_pat

pytestmark = [pytest.mark.mock, pytest.mark.integration, pytest.mark.workflow]

DEFAULT_SCRIPT = Path(
    r"C:\Users\E017093\v2_vpath_customer_workflows\customers\CLAAS_New\projects"
    r"\ground_guidance\scripts\fetch_polarion_document.py"
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def fetch_script() -> Path:
    path = Path(os.getenv("VPATH_FETCH_SCRIPT", str(DEFAULT_SCRIPT)))
    if not path.is_file():
        pytest.skip(f"customer fetch script not available: {path}")
    return path


@pytest.fixture(scope="module")
def live_server(app):
    """The mock on a random localhost port, plain HTTP, in a daemon thread."""
    port = _free_port()
    server = make_server("127.0.0.1", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


def _run_script(script: Path, base_url: str, out_dir: Path, verify_ssl: str = "false") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["POLARION_PERSONAL_ACCESS_TOKEN"] = make_fake_pat()
    argv = [
        sys.executable, str(script),
        "--base-url", base_url,
        "--project", PROJECT,
        "--space", SPACE,
        "--document", DOCUMENT,
        "--out-dir", str(out_dir),
        "--verify-ssl", verify_ssl,
    ]
    return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=300)


def test_real_fetch_script_reproduces_the_export(fetch_script, live_server, fixture_dump, tmp_path):
    result = _run_script(fetch_script, live_server, tmp_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "218 of 218 reported parts, 158 work items" in result.stdout

    dump = json.loads((tmp_path / "polarion_document_raw.json").read_text(encoding="utf-8"))
    assert dump["document"]["base_url"] == live_server
    assert dump["document"]["project"] == PROJECT
    assert dump["document"]["space"] == SPACE
    assert dump["document"]["name"] == DOCUMENT
    assert dump["document"]["part_count"] == dump["document"]["part_count_reported"] == 218
    assert dump["document"]["work_item_count"] == 158
    assert dump["parts"] == fixture_dump["parts"]
    assert dump["workitems"] == fixture_dump["workitems"]


def test_real_fetch_script_fails_hard_without_token(fetch_script, live_server, tmp_path):
    env = dict(os.environ)
    env.pop("POLARION_PERSONAL_ACCESS_TOKEN", None)
    argv = [sys.executable, str(fetch_script), "--base-url", live_server, "--project", PROJECT,
            "--space", SPACE, "--document", DOCUMENT, "--out-dir", str(tmp_path)]
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    assert "POLARION_PERSONAL_ACCESS_TOKEN is not set" in result.stderr


def test_real_fetch_script_reports_unknown_document(fetch_script, live_server, tmp_path):
    env = dict(os.environ)
    env["POLARION_PERSONAL_ACCESS_TOKEN"] = make_fake_pat()
    argv = [sys.executable, str(fetch_script), "--base-url", live_server, "--project", PROJECT,
            "--space", SPACE, "--document", "Does_Not_Exist", "--out-dir", str(tmp_path)]
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    assert "HTTP 404" in result.stderr
    assert not (tmp_path / "polarion_document_raw.json").exists()
