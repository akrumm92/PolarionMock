"""
Central data store for Polarion Mock Server
Manages all entities and their relationships
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import logging

from ..models.project import Project, ProjectStore
from ..models.workitem import WorkItem
from ..models.document import Document
from ..models.collection import Collection
from ..models.user import User

logger = logging.getLogger(__name__)


@dataclass
class DataStore:
    """Central data store for all Polarion entities."""
    
    projects: ProjectStore = field(default_factory=ProjectStore)
    workitems: Dict[str, WorkItem] = field(default_factory=dict)
    documents: Dict[str, Document] = field(default_factory=dict)
    collections: Dict[str, Collection] = field(default_factory=dict)
    users: Dict[str, User] = field(default_factory=dict)
    
    # Document parts tracking
    document_parts: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    # Work item counter for auto-generated IDs
    _workitem_counter: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize with dummy data."""
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
        
        logger.info("Data store seeding completed")
    
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
        ]
        
        for project_id, space_id, doc_id, title, description in documents_data:
            doc = Document.create_mock(
                project_id=project_id,
                space_id=space_id,
                document_id=doc_id,
                title=title,
                homePageContent={
                    "type": "text/html",
                    "value": f"<h1>{title}</h1><p>{description}</p>"
                }
            )
            self.documents[doc.id] = doc
            
            # Initialize empty document parts
            self.document_parts[doc.id] = []
    
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
                
                # Add to document parts
                self._add_workitem_to_document(module_id, workitem.id)
            
            self.workitems[workitem.id] = workitem
    
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
    
    def _add_workitem_to_document(self, document_id: str, workitem_id: str):
        """Add work item to document parts."""
        if document_id not in self.document_parts:
            self.document_parts[document_id] = []
        
        # Create document part
        part_id = f"{document_id}/part_{len(self.document_parts[document_id]) + 1}"
        part = {
            "type": "document_parts",
            "id": part_id,
            "attributes": {
                "type": "workitem"
            },
            "relationships": {
                "workItem": {
                    "data": {
                        "type": "workitems",
                        "id": workitem_id
                    }
                }
            }
        }
        
        self.document_parts[document_id].append(part)
    
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