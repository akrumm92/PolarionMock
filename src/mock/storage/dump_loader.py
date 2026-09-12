"""
Loader for raw Polarion document dumps.

A "dump" is the JSON file written by the read-only fetch script
``fetch_polarion_document.py`` (customer capsule, ground_guidance project):

.. code-block:: json

    {
      "document": {"name": "...", "project": "...", "space": "...", ...},
      "parts": [{"part_id": "heading_X-1", "part_type": "heading",
                 "content_html": "<h1 ...></h1>", "workitem_id": "X-1"}, ...],
      "workitems": [{"id": "X-1", "title": "...", "type": "heading",
                     "outlineNumber": "1", "status": "proposed",
                     "description_html": "<p>...</p>"}, ...]
    }

Every dump found in the dump directory is loaded into the in-memory data
store at start-up, so the mock serves exactly the document that was exported
from production: same project, same space, same document name, same parts in
the same order, same work items with the same attributes.

This is what makes a workflow reproducible offline: export once from the real
Polarion, drop the file into ``src/mock/mock_data/polarion_dumps/`` and point
the workflow's base URL at the mock.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

from ..models.document import Document
from ..models.project import Project
from ..models.workitem import WorkItem

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .data_store import DataStore

logger = logging.getLogger(__name__)

# Default location of the bundled dumps: src/mock/mock_data/polarion_dumps
DEFAULT_DUMP_DIR = Path(__file__).resolve().parents[1] / "mock_data" / "polarion_dumps"

# Environment variable that overrides / extends the dump directory list.
# Several directories can be given separated by ``os.pathsep``.
DUMP_DIR_ENV = "MOCK_DUMP_DIR"

_PREFIX_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)-\d+$")


class DumpFormatError(ValueError):
    """Raised when a dump file does not have the expected structure."""


def dump_directories() -> List[Path]:
    """Return the list of directories that are scanned for dumps.

    The bundled directory is always included; ``MOCK_DUMP_DIR`` adds more.
    """
    dirs: List[Path] = [DEFAULT_DUMP_DIR]
    extra = os.getenv(DUMP_DIR_ENV, "").strip()
    if extra:
        for item in extra.split(os.pathsep):
            item = item.strip()
            if item:
                dirs.append(Path(item))
    return dirs


def _tracker_prefix(workitems: Iterable[Dict[str, Any]], fallback: str) -> str:
    """Derive the tracker prefix (e.g. ``VPAT``) from the work item ids."""
    for item in workitems:
        match = _PREFIX_RE.match(str(item.get("id", "")))
        if match:
            return match.group(1)
    return fallback.upper()


def validate_dump(dump: Dict[str, Any]) -> None:
    """Check the minimal structure of a dump. Raise DumpFormatError otherwise."""
    if not isinstance(dump, dict):
        raise DumpFormatError("dump must be a JSON object")
    document = dump.get("document")
    if not isinstance(document, dict):
        raise DumpFormatError("dump.document is missing")
    for key in ("name", "project", "space"):
        if not document.get(key):
            raise DumpFormatError(f"dump.document.{key} is missing or empty")
    if not isinstance(dump.get("parts"), list):
        raise DumpFormatError("dump.parts must be a list")
    if not isinstance(dump.get("workitems"), list):
        raise DumpFormatError("dump.workitems must be a list")
    for index, part in enumerate(dump["parts"]):
        if not isinstance(part, dict) or not part.get("part_id") or not part.get("part_type"):
            raise DumpFormatError(f"dump.parts[{index}] needs part_id and part_type")
    for index, item in enumerate(dump["workitems"]):
        if not isinstance(item, dict) or not item.get("id"):
            raise DumpFormatError(f"dump.workitems[{index}] needs an id")


def load_dump(store: "DataStore", dump: Dict[str, Any], source: str = "<memory>") -> Dict[str, Any]:
    """Load one dump into ``store``. Idempotent: reloading replaces the document.

    Returns a summary dict with the document id and the number of parts and
    work items that were loaded.
    """
    validate_dump(dump)
    document_meta = dump["document"]
    project_id = str(document_meta["project"])
    space_id = str(document_meta["space"])
    document_name = str(document_meta["name"])
    document_id = f"{project_id}/{space_id}/{document_name}"

    # 1. Project (created on demand, tracker prefix derived from the ids)
    if not store.projects.get_by_id(project_id):
        prefix = _tracker_prefix(dump["workitems"], project_id)
        store.projects.create(
            Project.create_mock(
                project_id,
                project_id,
                description=f"Project {project_id} (loaded from Polarion dump {Path(source).name})",
                trackerPrefix=prefix,
            )
        )
        logger.info("Created project %s (prefix %s) from dump", project_id, prefix)

    # 2. Document (replace an existing one with the same id)
    document = Document.create_mock(
        project_id=project_id,
        space_id=space_id,
        document_id=document_name,
        title=document_name,
        type="generic",
        status="draft",
        homePageContent={"type": "text/html", "value": ""},
    )
    document.relationships = {
        "project": {"data": {"type": "projects", "id": project_id}},
    }
    store.documents[document_id] = document
    # Drop parts and work items of a previous load of the same document
    store.document_parts[document_id] = []
    for full_id in [
        wi_id
        for wi_id, wi in store.workitems.items()
        if wi.relationships
        and wi.relationships.get("module", {}).get("data", {}).get("id") == document_id
    ]:
        del store.workitems[full_id]

    # 3. Work items - exactly the attributes the export carried
    loaded_workitems = 0
    for item in dump["workitems"]:
        short_id = str(item["id"])
        description_html = item.get("description_html") or ""
        attributes: Dict[str, Any] = {
            "type": item.get("type") or "task",
            "status": item.get("status") or "proposed",
            "outlineNumber": item.get("outlineNumber"),
        }
        if description_html:
            attributes["description"] = {"type": "text/html", "value": description_html}
        workitem = WorkItem.create_mock(
            project_id=project_id,
            workitem_id=short_id,
            title=item.get("title") or "",
            **attributes,
        )
        workitem.relationships = {
            "project": {"data": {"type": "projects", "id": project_id}},
            "module": {"data": {"type": "documents", "id": document_id}},
        }
        workitem._is_in_document = True
        workitem._in_recycle_bin = False
        store.workitems[workitem.id] = workitem
        loaded_workitems += 1

    # 4. Parts - in document order, referencing the work items by full id
    loaded_parts = 0
    for position, part in enumerate(dump["parts"], start=1):
        workitem_ref = part.get("workitem_id")
        full_workitem_id = f"{project_id}/{workitem_ref}" if workitem_ref else None
        if full_workitem_id and full_workitem_id in store.workitems:
            store.workitems[full_workitem_id]._document_position = position
        store.add_part(
            document_id,
            part_id=str(part["part_id"]),
            part_type=str(part["part_type"]),
            content=part.get("content_html") or "",
            workitem_id=full_workitem_id,
            level=part.get("level"),
            external=part.get("external"),
        )
        loaded_parts += 1

    summary = {
        "source": source,
        "document_id": document_id,
        "project": project_id,
        "space": space_id,
        "document": document_name,
        "parts": loaded_parts,
        "workitems": loaded_workitems,
    }
    logger.info(
        "Loaded Polarion dump %s: %s (%d parts, %d work items)",
        source, document_id, loaded_parts, loaded_workitems,
    )
    return summary


def load_dump_file(store: "DataStore", path: Path) -> Dict[str, Any]:
    """Load a single dump file from disk."""
    with open(path, encoding="utf-8") as handle:
        dump = json.load(handle)
    return load_dump(store, dump, source=str(path))


def load_dump_directory(store: "DataStore", directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load every ``*.json`` dump below ``directory`` (default: all dump dirs).

    Files that are not dumps (wrong structure) are skipped with a warning so a
    stray JSON file never prevents the mock from starting.
    """
    directories = [directory] if directory else dump_directories()
    summaries: List[Dict[str, Any]] = []
    for base in directories:
        if not base.is_dir():
            logger.debug("Dump directory %s does not exist - skipped", base)
            continue
        for path in sorted(base.glob("*.json")):
            try:
                summaries.append(load_dump_file(store, path))
            except (DumpFormatError, json.JSONDecodeError) as error:
                logger.warning("Skipping %s: not a Polarion dump (%s)", path, error)
    return summaries
