"""
Work Item model for Polarion Mock Server
"""

from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from .common import Description, BaseResource


class WorkItemAttributes(BaseModel):
    """Work Item attributes following Polarion API specification."""
    title: str = Field(description="Work item title")
    description: Optional[Description] = Field(default=None, description="Work item description")
    type: str = Field(default="task", description="Work item type (task, requirement, defect, etc.)")
    status: str = Field(default="open", description="Work item status")
    priority: Optional[str] = Field(default="medium", description="Priority level")
    severity: Optional[str] = Field(default=None, description="Severity level")
    created: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    author: Optional[str] = Field(default=None, description="Author user ID")
    assignee: Optional[List[str]] = Field(default=None, description="Assignee user IDs")
    categories: Optional[List[str]] = Field(default=None, description="Category IDs")
    dueDate: Optional[datetime] = Field(default=None, description="Due date")
    plannedIn: Optional[List[str]] = Field(default=None, description="Planning IDs")
    resolution: Optional[str] = Field(default=None, description="Resolution")
    resolvedOn: Optional[datetime] = Field(default=None, description="Resolution date")
    outlineNumber: Optional[str] = Field(default=None, description="Outline number in document")
    hyperlinks: Optional[List[Dict[str, str]]] = Field(default=None, description="External links")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }


class WorkItem(BaseResource):
    """Work Item model representing a Polarion work item."""
    type: Literal["workitems"] = Field(default="workitems")
    attributes: WorkItemAttributes = Field(description="Work item attributes")
    
    def to_json_api(self) -> Dict[str, Any]:
        """Convert to JSON:API format."""
        data = {
            "type": self.type,
            "id": self.id
        }
        
        # Convert attributes to dict using Pydantic's model_dump
        if self.attributes:
            data["attributes"] = self.attributes.model_dump(exclude_none=True)
        
        if self.relationships:
            data["relationships"] = self.relationships
        
        if self.links:
            data["links"] = self.links
        
        if self.meta:
            data["meta"] = self.meta
        
        return data
    
    @classmethod
    def create_mock(cls, project_id: str, workitem_id: str, title: str, **kwargs) -> "WorkItem":
        """Create a mock work item for testing."""
        full_id = f"{project_id}/{workitem_id}"
        
        # Handle description - can be string or dict
        desc = kwargs.get("description")
        if desc:
            if isinstance(desc, str):
                description = Description(type="text/plain", value=desc)
            elif isinstance(desc, dict):
                description = Description(**desc)
            else:
                description = None
            kwargs["description"] = description
        
        attributes = WorkItemAttributes(
            title=title,
            **kwargs
        )
        
        return cls(
            id=full_id,
            attributes=attributes,
            links={
                "self": f"/polarion/rest/v1/projects/{project_id}/workitems/{workitem_id}",
                "portal": f"/polarion/#/project/{project_id}/workitem?id={workitem_id}"
            }
        )