"""
Test runs, test records and test steps (Polarion REST v1, read only).

``GET /projects/{p}/testruns``                        list (paged, ``query``,
                                                      ``templates``)
``GET /projects/{p}/testruns/{testRunId}``            one test run
``GET /projects/{p}/testruns/{testRunId}/testrecords``  its records (paged)
``GET /projects/{p}/workitems/{wi}/teststeps``        a test case's steps (paged)

Data: ``storage/demo_seed.py``. A work item without steps answers an empty
list.
"""

from typing import Any, Dict

from flask import Blueprint, request

from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError
from ..storage.data_store import data_store
from ..storage.demo_seed import DEMO_AUTHOR, DEMO_CREATED
from ..utils import lucene
from ..utils.listing import fields_of, list_response, project_url
from ..utils.listing import require_project, require_workitem, single_response
from ..utils.parts import apply_fields

bp = Blueprint("testruns", __name__)

_ATTRIBUTES = ("id", "title", "isTemplate", "status", "type", "selectTestCasesBy")


def _attributes(run: Dict[str, Any]) -> Dict[str, Any]:
    attributes = {key: run[key] for key in _ATTRIBUTES if run[key] is not None}
    attributes.update(created=DEMO_CREATED, updated=DEMO_CREATED)
    return attributes


def _render_run(run: Dict[str, Any]) -> Dict[str, Any]:
    project_id = run["project"]
    relationships: Dict[str, Any] = {
        "author": {"data": {"type": "users", "id": DEMO_AUTHOR}},
        "project": {"data": {"type": "projects", "id": project_id}},
    }
    if run["template"]:
        template_id = f"{project_id}/{run['template']}"
        relationships["template"] = {"data": {"type": "testruns", "id": template_id}}
    if run["document"]:
        document = {"type": "documents", "id": run["document"]}
        relationships["document"] = {"data": document}
    return {
        "type": "testruns",
        "id": f"{project_id}/{run['id']}",
        "attributes": apply_fields(_attributes(run), fields_of("testruns")),
        "relationships": relationships,
        "links": {"self": project_url(project_id, "testruns", run["id"])},
    }


def _run_or_404(project_id: str, run_id: str) -> Dict[str, Any]:
    require_project(project_id)
    run = data_store.testruns.get(f"{project_id}/{run_id}")
    if run is None:
        raise NotFoundError("testruns", f"{project_id}/{run_id}")
    return run


@bp.route("/projects/<project_id>/testruns", methods=["GET"])
@require_auth
def list_test_runs(project_id: str):
    require_project(project_id)
    templates = request.args.get("templates", "").lower() == "true"
    query = request.args.get("query")
    runs = [
        run
        for run in data_store.testruns.values()
        if run["project"] == project_id
        and run["isTemplate"] == templates
        and lucene.matches(_attributes(run), query)
    ]
    return list_response(runs, _render_run)


@bp.route("/projects/<project_id>/testruns/<run_id>", methods=["GET"])
@require_auth
def get_test_run(project_id: str, run_id: str):
    return single_response(_render_run(_run_or_404(project_id, run_id)))


@bp.route("/projects/<project_id>/testruns/<run_id>/testrecords", methods=["GET"])
@require_auth
def list_test_records(project_id: str, run_id: str):
    _run_or_404(project_id, run_id)
    run_full_id = f"{project_id}/{run_id}"
    records = list(data_store.test_records.get(run_full_id, []))
    case_project = request.args.get("testCaseProjectId")
    case_id = request.args.get("testCaseId")
    result = request.args.get("testResultId")
    if case_project:
        records = [r for r in records if r["testCase"].split("/")[0] == case_project]
    if case_id:
        records = [r for r in records if r["testCase"].split("/")[1] == case_id]
    if result:
        records = [r for r in records if r["result"] == result]
    fields = fields_of("testrecords")
    records_path = ("testruns", run_id, "testrecords")

    def render(record: Dict[str, Any]) -> Dict[str, Any]:
        case_project_id, case = record["testCase"].split("/", 1)
        tail = (case_project_id, case, str(record["iteration"]))
        attributes = {
            "iteration": record["iteration"],
            "result": record["result"],
            "executed": DEMO_CREATED,
        }
        return {
            "type": "testrecords",
            "id": "/".join((run_full_id,) + tail),
            "attributes": apply_fields(attributes, fields),
            "relationships": {
                "testCase": {"data": {"type": "workitems", "id": record["testCase"]}},
                "executedBy": {"data": {"type": "users", "id": DEMO_AUTHOR}},
            },
            "links": {"self": project_url(project_id, *records_path, *tail)},
        }

    return list_response(records, render)


@bp.route("/projects/<project_id>/workitems/<workitem_id>/teststeps", methods=["GET"])
@require_auth
def list_test_steps(project_id: str, workitem_id: str):
    full_id = require_workitem(project_id, workitem_id)
    steps = data_store.test_steps.get(full_id, [])
    fields = fields_of("teststeps")

    def render(indexed) -> Dict[str, Any]:
        index, columns = indexed
        attributes = {
            "index": str(index),
            "keys": list(columns),
            "values": [{"type": "text/html", "value": v} for v in columns.values()],
        }
        return {
            "type": "teststeps",
            "id": f"{full_id}/{index}",
            "attributes": apply_fields(attributes, fields),
            "links": {
                "self": project_url(
                    project_id, "workitems", workitem_id, "teststeps", str(index)
                )
            },
        }

    return list_response(list(enumerate(steps, start=1)), render)
