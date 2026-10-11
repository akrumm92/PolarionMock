"""
Demo data for the read endpoints a document dump does not carry.

A dump holds one document and its work items. Plans, test runs, collections
and attachments are seeded per dumped project from what the dump does hold
(its documents and work items) plus generic demo values (names, dates,
template ids). Nothing here pretends to be exported data.
"""

from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .data_store import DataStore

DEMO_AUTHOR = "admin"
DEMO_CREATED = "2026-01-05T08:00:00.000Z"


def dumped_documents(store: "DataStore") -> Dict[str, List[str]]:
    """Project id -> ids of its dumped documents, in load order."""
    projects: Dict[str, List[str]] = {}
    for summary in store.dump_summaries:
        projects.setdefault(summary["project"], []).append(summary["document_id"])
    return projects


def document_items(store: "DataStore", document_id: str) -> List[str]:
    """Full ids of the document's work items that are not headings, in order."""
    items = []
    for part in store.get_parts(document_id):
        full_id = part.get("workitem_id")
        workitem = store.workitems.get(full_id) if full_id else None
        if workitem and workitem.attributes.type != "heading":
            items.append(full_id)
    return items


def _plan(project_id: str, plan_id: str, name: str, **values) -> Dict:
    return {
        "project": project_id,
        "id": plan_id,
        "name": name,
        "isTemplate": values.get("isTemplate", False),
        "status": values.get("status"),
        "startDate": values.get("startDate"),
        "dueDate": values.get("dueDate"),
        "template": values.get("template"),
        "parent": values.get("parent"),
        "workitems": values.get("workitems", []),
    }


def seed_plans(store: "DataStore") -> None:
    """Release and Iteration templates, a release and its first iteration."""
    for project_id, documents in dumped_documents(store).items():
        items = [i for d in documents for i in document_items(store, d)]
        plans = [
            _plan(project_id, "release", "Release", isTemplate=True),
            _plan(project_id, "iteration", "Iteration", isTemplate=True),
            _plan(
                project_id,
                "Release_1",
                "Release 1",
                status="open",
                startDate="2026-01-05",
                dueDate="2026-06-30",
                template="release",
                workitems=items,
            ),
            _plan(
                project_id,
                "Iteration_1",
                "Iteration 1",
                status="open",
                startDate="2026-01-05",
                dueDate="2026-02-27",
                template="iteration",
                parent="Release_1",
                workitems=items[:5],
            ),
        ]
        for plan in plans:
            store.plans[f"{project_id}/{plan['id']}"] = plan


def _test_cases(store: "DataStore", project_id: str) -> List[str]:
    return [
        workitem.id
        for workitem in store.workitems.values()
        if workitem.id.startswith(f"{project_id}/")
        and workitem.attributes.type == "testcase"
    ]


def _test_run(project_id: str, run_id: str, title: str, **values) -> Dict:
    return {
        "project": project_id,
        "id": run_id,
        "title": title,
        "isTemplate": values.get("isTemplate", False),
        "status": values.get("status"),
        "type": values.get("type", "manual"),
        "selectTestCasesBy": values.get("selectTestCasesBy", "manualSelection"),
        "document": values.get("document"),
        "template": values.get("template"),
    }


def seed_testing(store: "DataStore") -> None:
    """A Manual Test template and one run per dumped project or project with
    test cases; the run records a pass for each test case, every test case
    gets two generic steps."""
    projects = dumped_documents(store)
    for workitem in store.workitems.values():
        if workitem.attributes.type == "testcase":
            projects.setdefault(workitem.id.split("/", 1)[0], [])
    for project_id, documents in projects.items():
        title = f"Test of {documents[0].rsplit('/', 1)[1]}" if documents else "Test"
        runs = [
            _test_run(project_id, "manual", "Manual Test", isTemplate=True),
            _test_run(
                project_id,
                "TestRun_1",
                title,
                status="open",
                template="manual",
                document=documents[0] if documents else None,
                selectTestCasesBy="staticLiveDoc" if documents else "manualSelection",
            ),
        ]
        for run in runs:
            store.testruns[f"{project_id}/{run['id']}"] = run
        cases = _test_cases(store, project_id)
        store.test_records[f"{project_id}/TestRun_1"] = [
            {"testCase": case, "iteration": 0, "result": "passed"} for case in cases
        ]
        for case in cases:
            store.test_steps[case] = [
                {"step": "Prepare the test setup.", "expectedResult": "Setup ready."},
                {
                    "step": "Execute the test case.",
                    "expectedResult": "The system behaves as specified.",
                },
            ]


def attachment_key(kind: str, owner_id: str) -> str:
    """Key of an owner's attachments: ``workitem``/``document``/``testrun``."""
    return f"{kind}:{owner_id}"


def _attachment(file_name: str, text: str) -> Dict:
    return {
        "id": f"1-{file_name}",
        "fileName": file_name,
        "title": file_name,
        "content": text.encode("utf-8"),
    }


def seed_attachments(store: "DataStore") -> None:
    """A generic text attachment on each dumped document, on its first work
    item that is not a heading and on the project's TestRun_1."""
    for project_id, documents in dumped_documents(store).items():
        owners = []
        for document_id in documents:
            owners.append(("document", document_id))
            items = document_items(store, document_id)
            if items:
                owners.append(("workitem", items[0]))
        if f"{project_id}/TestRun_1" in store.testruns:
            owners.append(("testrun", f"{project_id}/TestRun_1"))
        for kind, owner_id in owners:
            text = f"Demo attachment of {kind} {owner_id}.\n"
            store.attachments[attachment_key(kind, owner_id)] = [
                _attachment("notes.txt", text)
            ]


def seed_demo_data(store: "DataStore") -> None:
    seed_plans(store)
    seed_testing(store)
    seed_attachments(store)
