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


def seed_demo_data(store: "DataStore") -> None:
    seed_plans(store)
