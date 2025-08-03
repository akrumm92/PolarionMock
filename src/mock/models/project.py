"""
Project model for Polarion Mock Server
"""

from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class ProjectDescription(BaseModel):
    """Project description with type and value."""
    type: str = Field(default="text/plain", description="Content type")
    value: str = Field(description="Description content")


class ProjectAttributes(BaseModel):
    """Project attributes following Polarion API specification."""
    id: str = Field(description="Project ID")
    name: str = Field(description="Project name")
    description: Optional[ProjectDescription] = Field(default=None, description="Project description")
    created: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    active: bool = Field(default=True, description="Whether project is active")
    trackerPrefix: Optional[str] = Field(default=None, description="Tracker prefix for work items")
    version: Optional[str] = Field(default="1.0.0", description="Project version")
    location: Optional[str] = Field(default=None, description="Project location path")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }


class Project(BaseModel):
    """Project model representing a Polarion project."""
    type: Literal["projects"] = Field(default="projects")
    id: str = Field(description="Project ID")
    attributes: ProjectAttributes = Field(description="Project attributes")
    relationships: Optional[Dict[str, Any]] = Field(default=None, description="Related resources")
    links: Optional[Dict[str, str]] = Field(default=None, description="Resource links")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Metadata")
    
    def to_json_api(self) -> Dict[str, Any]:
        """Convert to JSON:API format."""
        data = {
            "type": self.type,
            "id": self.id,
            "attributes": self.attributes.dict(exclude_none=True)
        }
        
        if self.relationships:
            data["relationships"] = self.relationships
        
        if self.links:
            data["links"] = self.links
        else:
            # Generate default links
            data["links"] = {
                "self": f"/polarion/rest/v1/projects/{self.id}",
                "portal": f"/polarion/#/project/{self.id}"
            }
        
        if self.meta:
            data["meta"] = self.meta
        
        return data
    
    @classmethod
    def create_mock(cls, project_id: str, name: Optional[str] = None, **kwargs) -> "Project":
        """Create a mock project for testing."""
        if not name:
            name = f"Test Project {project_id}"
        
        attributes = ProjectAttributes(
            id=project_id,
            name=name,
            description=ProjectDescription(
                type="text/plain",
                value=kwargs.get("description", f"Description for {name}")
            ),
            trackerPrefix=kwargs.get("trackerPrefix", project_id.upper()),
            **{k: v for k, v in kwargs.items() if k not in ["description", "trackerPrefix"]}
        )
        
        return cls(
            id=project_id,
            attributes=attributes
        )


@dataclass
class ProjectStore:
    """In-memory store for projects."""
    projects: Dict[str, Project] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize with default projects."""
        self.seed_data()
    
    def seed_data(self):
        """Seed the store with default projects."""
        default_projects = [
            Project.create_mock("elibrary", "eLibrary", 
                              description="Electronic Library System",
                              trackerPrefix="ELIB"),
            Project.create_mock("myproject", "My Project",
                              description="Sample test project",
                              trackerPrefix="MP"),
            Project.create_mock("testing", "Testing Project",
                              description="Project for testing purposes",
                              trackerPrefix="TEST"),
        ]
        
        for project in default_projects:
            self.projects[project.id] = project
    
    def get_all(self) -> List[Project]:
        """Get all projects."""
        return list(self.projects.values())
    
    def get_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return self.projects.get(project_id)
    
    def create(self, project: Project) -> Project:
        """Create a new project."""
        if project.id in self.projects:
            raise ValueError(f"Project with id '{project.id}' already exists")
        
        self.projects[project.id] = project
        return project
    
    def update(self, project_id: str, updates: Dict[str, Any]) -> Optional[Project]:
        """Update an existing project."""
        project = self.projects.get(project_id)
        if not project:
            return None
        
        # Update attributes
        for key, value in updates.items():
            if hasattr(project.attributes, key):
                setattr(project.attributes, key, value)
        
        project.attributes.updated = datetime.utcnow()
        return project
    
    def delete(self, project_id: str) -> bool:
        """Delete a project."""
        if project_id in self.projects:
            del self.projects[project_id]
            return True
        return False