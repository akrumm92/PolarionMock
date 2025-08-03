"""
Document model for Polarion Mock Server
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from .common import Description, BaseResource


class DocumentAttributes(BaseModel):
    """Document attributes following Polarion API specification."""
    title: str = Field(description="Document title")
    name: str = Field(description="Document name/ID")
    type: str = Field(default="generic", description="Document type")
    status: str = Field(default="draft", description="Document status")
    created: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    author: Optional[str] = Field(default=None, description="Author user ID")
    homePageContent: Optional[Description] = Field(default=None, description="Document content")
    renderingLayouts: Optional[List[str]] = Field(default=None, description="Available layouts")
    structureLinkRole: Optional[str] = Field(default="parent", description="Structure link role")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }


class Document(BaseResource):
    """Document model representing a Polarion document."""
    type: str = Field(default="documents", const=True)
    attributes: DocumentAttributes = Field(description="Document attributes")
    
    @classmethod
    def create_mock(cls, project_id: str, space_id: str, document_id: str, title: str, **kwargs) -> "Document":
        """Create a mock document for testing."""
        full_id = f"{project_id}/{space_id}/{document_id}"
        
        attributes = DocumentAttributes(
            title=title,
            name=document_id,
            **kwargs
        )
        
        return cls(
            id=full_id,
            attributes=attributes,
            links={
                "self": f"/polarion/rest/v1/projects/{project_id}/spaces/{space_id}/documents/{document_id}",
                "portal": f"/polarion/#/project/{project_id}/wiki/{document_id}"
            }
        )