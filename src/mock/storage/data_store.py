"""
Central data store for Polarion Mock Server
Manages all entities and their relationships.

Document parts are kept in ONE canonical internal shape per part::

    {
        "id": "heading_VPAT-11137",        # short part id (= attributes.id)
        "type": "heading",                 # heading | workitem | normal | ...
        "content": "<h1 ...></h1>",        # attributes.content (HTML)
        "workitem_id": "VPATHAI/VPAT-11137" or None,   # full work item id
        "level": None, "external": None    # optional extras from a dump
    }

The JSON:API rendering (ids, links, relationships, sparse fieldsets) is done
in ``src/mock/utils/parts.py`` so every producer (seed data, dump loader,
POST /parts, moveToDocument) stores the same thing and every consumer reads
the same thing.
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import logging

from ..models.project import Project, ProjectStore
from ..models.workitem import WorkItem
from ..models.document import Document
from ..models.collection import Collection
from ..models.user import User
from ..models.common import Description
from .document_body import render_body, split_body

logger = logging.getLogger(__name__)

# Lucene ``id:`` clause of a work item query and the ids it names
_ID_CLAUSE = re.compile(r'(?<![\w.])id:(\([^)]*\)|"[^"]*"|[^\s()]+)')
_ID_VALUE = re.compile(r'[^\s()"]+')


def make_part(part_id: str, part_type: str, content: str = "",
              workitem_id: Optional[str] = None,
              level: Optional[int] = None,
              external: Optional[bool] = None) -> Dict[str, Any]:
    """Build a canonical document part dict."""
    return {
        "id": part_id,
        "type": part_type,
        "content": content or "",
        "workitem_id": workitem_id,
        "level": level,
        "external": external,
    }


@dataclass
class DataStore:
    """Central data store for all Polarion entities."""

    projects: ProjectStore = field(default_factory=ProjectStore)
    workitems: Dict[str, WorkItem] = field(default_factory=dict)
    documents: Dict[str, Document] = field(default_factory=dict)
    collections: Dict[str, Collection] = field(default_factory=dict)
    users: Dict[str, User] = field(default_factory=dict)

    # Document parts: document id -> ordered list of canonical part dicts
    document_parts: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Work item comments: work item id -> comments, oldest first
    comments: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Work item counter for auto-generated IDs
    _workitem_counter: Dict[str, int] = field(default_factory=dict)

    # Summaries of the Polarion dumps loaded from disk (see dump_loader)
    dump_summaries: List[Dict[str, Any]] = field(default_factory=list)

    # Read-only demo data the dumps do not carry (see demo_seed)
    plans: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize with dummy data."""
        self.seed_dummy_data()

    # ------------------------------------------------------------------ seeding
    def reset(self) -> None:
        """Drop everything and seed again (dummy data + dumps from disk)."""
        # Clear IN PLACE: the blueprints keep references to these containers
        # (e.g. projects.py binds data_store.projects at import time).
        self.projects.projects.clear()
        self.projects.seed_data()
        self.workitems.clear()
        self.documents.clear()
        self.collections.clear()
        self.users.clear()
        self.document_parts.clear()
        self.comments.clear()
        self._workitem_counter.clear()
        self.dump_summaries.clear()
        self.plans.clear()
        self.seed_dummy_data()

    def seed_dummy_data(self):
        """Seed the store with comprehensive dummy data."""
        logger.info("Seeding data store with dummy data...")

        # Create users
        self._create_dummy_users()

        # Create projects (already handled by ProjectStore)
        # Add more test projects including Python project from requirements
        test_projects = [
            Project.create_mock("Python", "Python Project",
                              description="Python functional safety project",
                              trackerPrefix="FCTS"),
            Project.create_mock("automotive", "Automotive Project",
                              description="Automotive safety requirements",
                              trackerPrefix="AUTO"),
            Project.create_mock("medical", "Medical Device Project",
                              description="Medical device compliance",
                              trackerPrefix="MED"),
            # Sandbox project used by tests/test_mock_workitem_document_integration.py
            Project.create_mock("TestProject", "Test Project",
                              description="Sandbox for the two-step work item / document tests",
                              trackerPrefix="TP"),
        ]

        for project in test_projects:
            try:
                self.projects.create(project)
            except ValueError:
                pass  # Project already exists

        # Create documents
        self._create_dummy_documents()

        # Create work items
        self._create_dummy_workitems()

        # Create collections
        self._create_dummy_collections()

        # Load real Polarion document dumps (exports of the fetch script)
        self._load_dumps()

        # Plans, test runs, ... for the dumped projects
        from .demo_seed import seed_demo_data  # local import: avoids a cycle
        seed_demo_data(self)

        logger.info("Data store seeding completed")

    def _load_dumps(self) -> None:
        """Load every Polarion dump from the dump directories."""
        from .dump_loader import load_dump_directory  # local import: avoids a cycle
        try:
            self.dump_summaries = load_dump_directory(self)
        except Exception:  # pragma: no cover - never let a bad dump kill the server
            logger.exception("Loading Polarion dumps failed")
            self.dump_summaries = []
        for summary in self.dump_summaries:
            logger.info("Dump available: %s (%d parts, %d work items)",
                        summary["document_id"], summary["parts"], summary["workitems"])

    def load_dump(self, dump: Dict[str, Any], source: str = "<api>") -> Dict[str, Any]:
        """Load one dump dict at runtime (admin endpoint)."""
        from .dump_loader import load_dump
        summary = load_dump(self, dump, source=source)
        # replace an older summary of the same document
        self.dump_summaries = [
            s for s in self.dump_summaries if s["document_id"] != summary["document_id"]
        ] + [summary]
        return summary

    def _create_dummy_users(self):
        """Create dummy users."""
        users = [
            User.create_mock("admin", "Administrator", email="admin@example.com"),
            User.create_mock("john.doe", "John Doe", email="john.doe@example.com"),
            User.create_mock("jane.smith", "Jane Smith", email="jane.smith@example.com"),
            User.create_mock("test.user", "Test User", email="test.user@example.com"),
        ]

        for user in users:
            self.users[user.id] = user

    def _create_dummy_documents(self):
        """Create dummy documents following real Polarion structure."""
        documents_data = [
            # Python project documents (matching real data from requirements)
            ("Python", "Component Layer", "Component Requirement Specification",
             "Component Requirement Specification",
             "Component requirements document"),
            ("Python", "Domain Layer", "Software Requirement Specification",
             "Software Requirement Specification",
             "Software requirements document"),
            ("Python", "Functional Layer", "Functional Concept",
             "Functional Concept",
             "Functional concept document"),
            ("Python", "Product Layer", "Product Requirements Specification",
             "Product Requirements Specification",
             "Product requirements document"),

            # Python _default space document (for tests)
            ("Python", "_default", "Functional Concept - Template",
             "Functional Concept - Template",
             "Template document for functional concepts"),

            # eLibrary project documents
            ("elibrary", "_default", "requirements", "Requirements Specification",
             "Requirements document for eLibrary system"),
            ("elibrary", "_default", "architecture", "System Architecture",
             "System architecture and design"),
            ("elibrary", "testing", "test_plan", "Test Plan",
             "Comprehensive test plan for eLibrary"),

            # myproject documents
            ("myproject", "_default", "user_stories", "User Stories",
             "Collection of user stories"),
            ("myproject", "docs", "api_spec", "API Specification",
             "REST API specification document"),

            # automotive project documents
            ("automotive", "_default", "safety_req", "Safety Requirements",
             "ISO 26262 safety requirements"),
            ("automotive", "testing", "test_cases", "Test Cases",
             "Safety test cases"),

            # sandbox document for the two-step integration tests
            ("TestProject", "TestSpace", "TestDocument", "Test Document",
             "Empty sandbox document"),
        ]

        for project_id, space_id, doc_id, title, description in documents_data:
            doc = Document.create_mock(
                project_id=project_id,
                space_id=space_id,
                document_id=doc_id,
                title=title,
            )
            self.documents[doc.id] = doc
            self.set_document_body(
                doc.id,
                f'<h1 id="polarion_1">{title}</h1><p id="polarion_2">{description}</p>',
            )

    def _create_dummy_workitems(self):
        """Create dummy work items with various types and states.

        IMPORTANT: Every work item MUST have a module relationship (100% as per requirements).
        """
        workitems_data = [
            # Python project work items (150+ for pagination testing)
            *self._generate_python_workitems(),

            # eLibrary work items
            ("elibrary", "ELIB-1", "requirement", "User Authentication",
             "Users shall be able to authenticate using email and password",
             "open", "high", None, "elibrary/_default/requirements"),

            ("elibrary", "ELIB-2", "requirement", "Book Search",
             "Users shall be able to search books by title, author, or ISBN",
             "open", "high", None, "elibrary/_default/requirements"),

            ("elibrary", "ELIB-3", "defect", "Login Button Not Responsive",
             "Login button does not respond on mobile devices",
             "open", "critical", "major", "elibrary/_default/requirements"),

            ("elibrary", "ELIB-4", "task", "Setup CI/CD Pipeline",
             "Configure automated build and deployment pipeline",
             "done", "medium", None, "elibrary/_default/architecture"),

            # myproject work items
            ("myproject", "MP-1", "userstory", "As a user, I want to login",
             "User story for authentication feature",
             "open", "high", None, "myproject/_default/user_stories"),

            ("myproject", "MP-2", "task", "Implement REST API",
             "Create RESTful API endpoints",
             "in_progress", "high", None, "myproject/docs/api_spec"),

            ("myproject", "MP-3", "defect", "API returns 500 error",
             "POST /api/users returns internal server error",
             "open", "high", "critical", "myproject/docs/api_spec"),

            # automotive work items
            ("automotive", "AUTO-1", "requirement", "Emergency Braking",
             "System shall engage emergency braking when obstacle detected",
             "approved", "critical", None, "automotive/_default/safety_req"),

            ("automotive", "AUTO-2", "testcase", "Test Emergency Braking",
             "Verify emergency braking engages within 100ms",
             "draft", "high", None, "automotive/testing/test_cases"),
        ]

        for (project_id, work_id, w_type, title, description,
             status, priority, severity, module_id) in workitems_data:

            # Build work item attributes
            attrs = {
                "type": w_type,
                "status": status,
                "priority": priority,
                "author": "admin",
                "assignee": ["john.doe"] if status != "done" else ["jane.smith"]
            }

            # Handle description format (can be string or object)
            if isinstance(description, dict):
                attrs["description"] = description
            else:
                attrs["description"] = {
                    "type": "text/html",
                    "value": description
                }

            if severity:
                attrs["severity"] = severity

            # Create work item
            workitem = WorkItem.create_mock(
                project_id=project_id,
                workitem_id=work_id,
                title=title,
                **attrs
            )

            # Add module relationship if specified
            if module_id:
                workitem.relationships = {
                    "module": {
                        "data": {
                            "type": "documents",
                            "id": module_id
                        }
                    }
                }

            self.workitems[workitem.id] = workitem

            # Add to document parts (the seeded items are visible in their document)
            if module_id:
                self._add_workitem_to_document(module_id, workitem.id)

    def _generate_python_workitems(self):
        """Generate 150+ Python project work items for pagination testing."""
        workitems = []

        # Document mapping for Python project
        documents = [
            ("Python/Component Layer/Component Requirement Specification", "componentrequirement"),
            ("Python/Domain Layer/Software Requirement Specification", "softwarerequirement"),
            ("Python/Functional Layer/Functional Concept", "functionalrequirement"),
            ("Python/Product Layer/Product Requirements Specification", "technicalrequirement"),
        ]

        # Status and priority options from real data
        statuses = ["proposed", "approved", "implemented", "verified"]
        priorities = ["50.0", "100.0", "150.0", "200.0"]
        severities = ["not_applicable", "minor", "major", "critical"]

        # Generate 150+ work items
        for i in range(1, 155):
            doc_idx = i % len(documents)
            doc_id, w_type = documents[doc_idx]

            # Create work item data
            workitems.append((
                "Python",
                f"FCTS-{9000 + i}",
                w_type,
                f"Functional Safety Requirement {i}",
                {
                    "type": "text/html",
                    "value": f"<p>Safety Attributes need to be filled out for requirement {i}</p>"
                },
                statuses[i % len(statuses)],
                priorities[i % len(priorities)],
                severities[i % len(severities)],
                doc_id
            ))

        return workitems

    def _create_dummy_collections(self):
        """Create dummy collections."""
        collections_data = [
            ("elibrary", "sprint_1", "Sprint 1", "First sprint items",
             "type:task AND status:open"),
            ("myproject", "critical_bugs", "Critical Bugs", "High priority defects",
             "type:defect AND priority:critical"),
            ("automotive", "safety_critical", "Safety Critical", "Safety critical requirements",
             "type:requirement AND severity:critical"),
        ]

        for project_id, coll_id, name, description, query in collections_data:
            collection = Collection.create_mock(
                project_id=project_id,
                collection_id=coll_id,
                name=name,
                description=description,
                query=query
            )
            self.collections[collection.id] = collection

    # ------------------------------------------------------------ document parts
    def add_part(self, document_id: str, part_id: str, part_type: str,
                 content: str = "", workitem_id: Optional[str] = None,
                 position: Optional[int] = None,
                 level: Optional[int] = None,
                 external: Optional[bool] = None) -> Dict[str, Any]:
        """Store a canonical part for ``document_id``.

        ``position`` is 1-based; ``None`` appends. A part with the same short
        id replaces the existing one (a work item appears once in a document).
        """
        parts = self.document_parts.setdefault(document_id, [])
        parts[:] = [p for p in parts if p["id"] != part_id]
        part = make_part(part_id, part_type, content, workitem_id, level, external)
        if position is None or position > len(parts):
            parts.append(part)
        else:
            parts.insert(max(position - 1, 0), part)
        return part

    def document_body(self, document_id: str) -> str:
        """The document's text (``homePageContent``), made of its visible parts."""
        return render_body([part["content"] for part in self.get_parts(document_id)])

    def set_document_body(self, document_id: str, html: Optional[str]) -> None:
        """Write the document's text: its parts become the blocks of ``html``.

        A work item whose macro is new in the text enters the document; one
        whose macro left the text goes to the document's Recycle Bin.
        Raises ``ValueError`` (nothing changed) for a macro naming an unknown
        work item.
        """
        project_id = document_id.split("/", 1)[0]
        parts = split_body(html or "", project_id)
        for part in parts:
            if part["workitem_id"] and part["workitem_id"] not in self.workitems:
                raise ValueError(
                    f"the document text references work item {part['workitem_id']}, "
                    "which does not exist"
                )
        kept = {part["workitem_id"] for part in parts if part["workitem_id"]}
        for old in self.document_parts.get(document_id, []):
            workitem = self.workitems.get(old.get("workitem_id") or "")
            if workitem is not None and workitem.id not in kept:
                workitem._is_in_document = False
                workitem._in_recycle_bin = True
        stored = []
        for position, part in enumerate(parts, start=1):
            workitem = self.workitems.get(part["workitem_id"] or "")
            if workitem is not None:
                workitem._is_in_document = True
                workitem._in_recycle_bin = False
                workitem._document_position = position
                if not part["external"]:
                    workitem.relationships = {
                        **(workitem.relationships or {}),
                        "module": {"data": {"type": "documents", "id": document_id}},
                    }
            stored.append(make_part(part["id"], part["type"], part["content"],
                                    part["workitem_id"], external=part["external"]))
        self.document_parts[document_id] = stored

    def document_resource(self, document: Document) -> Dict[str, Any]:
        """A document as JSON:API resource, its text rendered from its parts."""
        document.attributes.homePageContent = Description(
            type="text/html", value=self.document_body(document.id)
        )
        return document.to_json_api()

    def get_parts(self, document_id: str, include_recycled: bool = False) -> List[Dict[str, Any]]:
        """Ordered, visible parts of a document.

        A part that references a work item is visible only while that work
        item is in the document (not in the Recycle Bin).
        """
        visible: List[Dict[str, Any]] = []
        for part in self.document_parts.get(document_id, []):
            workitem_id = part.get("workitem_id")
            if workitem_id and not include_recycled:
                workitem = self.workitems.get(workitem_id)
                if workitem is None or not getattr(workitem, "_is_in_document", False):
                    continue
            visible.append(part)
        return visible

    def find_part(self, document_id: str, part_ref: str) -> Optional[int]:
        """Index of a part addressed by short id or full id, or None."""
        for index, part in enumerate(self.document_parts.get(document_id, [])):
            if part["id"] == part_ref or f"{document_id}/{part['id']}" == part_ref:
                return index
        return None

    def remove_parts_for_workitem(self, workitem_id: str) -> int:
        """Remove every part referencing ``workitem_id``; return the count."""
        removed = 0
        for document_id, parts in self.document_parts.items():
            before = len(parts)
            parts[:] = [p for p in parts if p.get("workitem_id") != workitem_id]
            removed += before - len(parts)
        return removed

    def backlinks_of(self, workitem_id: str) -> List[Dict[str, Any]]:
        """The links stored on other work items that point to ``workitem_id``."""
        found = []
        for source in self.workitems.values():
            for link in getattr(source, "linkedWorkItems", None) or []:
                target = link.get("relationships", {}).get("workItem", {}).get("data", {})
                if target.get("id") == workitem_id:
                    found.append(link)
        return found

    def delete_workitem(self, workitem_id: str) -> None:
        """Delete a work item and take it out of every document."""
        self.remove_parts_for_workitem(workitem_id)
        self.comments.pop(workitem_id, None)
        del self.workitems[workitem_id]

    def _add_workitem_to_document(self, document_id: str, workitem_id: str,
                                  position: Optional[int] = None) -> Dict[str, Any]:
        """Add a work item to a document (creates the part, marks it visible)."""
        short_id = workitem_id.split("/", 1)[-1]
        workitem = self.workitems.get(workitem_id)
        part_type = "workitem"
        content = f'<div id="polarion_wiki macro name=module-workitem;params=id={short_id}"></div>'
        if workitem is not None:
            if getattr(workitem.attributes, "type", "") == "heading":
                part_type = "heading"
                content = f'<h2 id="polarion_wiki macro name=module-workitem;params=id={short_id}"></h2>'
            workitem._is_in_document = True
            workitem._in_recycle_bin = False
        part = self.add_part(
            document_id,
            part_id=f"{part_type}_{short_id}",
            part_type=part_type,
            content=content,
            workitem_id=workitem_id,
            position=position,
        )
        if workitem is not None:
            workitem._document_position = self.find_part(document_id, part["id"]) + 1
        return part

    def get_next_workitem_id(self, project_id: str) -> str:
        """Generate next work item ID for a project."""
        if project_id not in self._workitem_counter:
            # Find highest existing ID for this project
            max_id = 0
            prefix = self.projects.get_by_id(project_id).attributes.trackerPrefix

            for wi_id in self.workitems:
                if wi_id.startswith(f"{project_id}/"):
                    parts = wi_id.split("/")[1].split("-")
                    if len(parts) > 1 and parts[0] == prefix:
                        try:
                            num = int(parts[1])
                            max_id = max(max_id, num)
                        except ValueError:
                            pass

            self._workitem_counter[project_id] = max_id

        self._workitem_counter[project_id] += 1
        project = self.projects.get_by_id(project_id)
        prefix = project.attributes.trackerPrefix if project else project_id.upper()

        return f"{prefix}-{self._workitem_counter[project_id]}"

    def query_workitems(self, query: Optional[str] = None,
                       project_id: Optional[str] = None) -> List[WorkItem]:
        """Query work items with optional filtering."""
        results = list(self.workitems.values())

        # Filter by project
        if project_id:
            results = [wi for wi in results if wi.id.startswith(f"{project_id}/")]

        # id:X / id:(X Y ...) / id:"PROJ/X" - by work item id, with or without project
        if query:
            id_clause = _ID_CLAUSE.search(query)
            if id_clause:
                wanted = set(_ID_VALUE.findall(id_clause.group(1))) - {"OR"}
                results = [wi for wi in results
                           if wi.id in wanted or wi.id.split("/", 1)[-1] in wanted]
                query = (query[:id_clause.start()] + query[id_clause.end():]).strip()
                query = re.sub(r"^(AND\s+)+|(\s+AND)+$", "", query).strip()

        # Simple query parsing (real implementation would be more complex)
        if query:
            # Handle module.id query
            if "module.id:" in query:
                module_id = query.split("module.id:")[1].strip()
                results = [wi for wi in results
                          if wi.relationships and
                          wi.relationships.get("module", {}).get("data", {}).get("id") == module_id]

            # Handle type queries
            elif "type:" in query:
                q_type = query.split("type:")[1].split()[0]
                results = [wi for wi in results if wi.attributes.type == q_type]

            # Handle status queries
            elif "status:" in query:
                q_status = query.split("status:")[1].split()[0]
                results = [wi for wi in results if wi.attributes.status == q_status]

        return results


# Global data store instance
data_store = DataStore()
