"""
Work Item model for Polarion Mock Server
"""

from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from .common import Description, BaseResource


class WorkItemAttributes(BaseModel):
    """Work Item attributes following Polarion API specification.
    
    Based on real Polarion data from MOCK_IMPLEMENTATION_REQUIREMENTS.md:
    - type: technicalrequirement, functionalrequirement, componentrequirement, softwarerequirement
    - status: proposed, approved, implemented, verified
    - priority: String with decimal (e.g., "50.0", "100.0")
    - severity: not_applicable, minor, major, critical
    """
    id: Optional[str] = Field(default=None, description="Work item ID (without project prefix)")
    title: str = Field(description="Work item title")
    description: Optional[Description] = Field(default=None, description="Work item description")
    type: str = Field(default="task", description="Work item type")
    status: str = Field(default="proposed", description="Work item status")
    priority: Optional[str] = Field(default="50.0", description="Priority as decimal string")
    severity: Optional[str] = Field(default="not_applicable", description="Severity level")
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
    customFields: Optional[str] = Field(default=None, description="Custom fields as JSON string")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }


class WorkItem(BaseResource):
    """Work Item model representing a Polarion work item."""
    type: Literal["workitems"] = Field(default="workitems")
    attributes: WorkItemAttributes = Field(description="Work item attributes")
    
    # Mock-specific tracking fields (not exposed in API responses)
    _is_in_document: bool = Field(default=False, exclude=True, description="Tracks if document part was created")
    _document_position: Optional[int] = Field(default=None, exclude=True, description="Position in document")
    _parent_workitem_id: Optional[str] = Field(default=None, exclude=True, description="Parent in hierarchy")
    _in_recycle_bin: bool = Field(default=False, exclude=True, description="WorkItem in recycle bin state")
    
    def to_json_api(self) -> Dict[str, Any]:
        """Convert to JSON:API format."""
        data = {
            "type": self.type,
            "id": self.id
        }
        
        # Convert attributes to dict using Pydantic's model_dump
        if self.attributes:
            attrs = self.attributes.model_dump(exclude_none=True)
            
            # Critical: Only include outlineNumber if WorkItem is in document
            # This replicates Polarion's behavior where WorkItems in "Recycle Bin" have no outline
            if not self._is_in_document and "outlineNumber" in attrs:
                del attrs["outlineNumber"]
            
            data["attributes"] = attrs
        
        if self.relationships:
            data["relationships"] = self.relationships
        
        if self.links:
            data["links"] = self.links
        
        if self.meta:
            data["meta"] = self.meta
        
        return data
    
    @classmethod
    def create_mock(cls, project_id: str, workitem_id: str, title: str, **kwargs) -> "WorkItem":
        """Create a mock work item for testing.
        
        Ensures work item follows real Polarion format:
        - ID format: project/workitem (e.g., "Python/FCTS-9345")
        - Description is always an object with type and value
        - Priority is a decimal string
        """
        full_id = f"{project_id}/{workitem_id}"
        
        # Set work item ID attribute (without project prefix)
        kwargs["id"] = workitem_id
        
        # Handle description - ensure it's always an object
        desc = kwargs.get("description")
        if desc:
            if isinstance(desc, str):
                description = Description(type="text/html", value=desc)
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