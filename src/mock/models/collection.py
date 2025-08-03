"""
Collection model for Polarion Mock Server
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from .common import Description, BaseResource


class CollectionAttributes(BaseModel):
    """Collection attributes following Polarion API specification."""
    id: str = Field(description="Collection ID")
    name: str = Field(description="Collection name")
    description: Optional[Description] = Field(default=None, description="Collection description")
    created: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    closedOn: Optional[datetime] = Field(default=None, description="Closure timestamp")
    query: Optional[str] = Field(default=None, description="Collection query")
    sortBy: Optional[str] = Field(default=None, description="Sort criteria")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }


class Collection(BaseResource):
    """Collection model representing a Polarion collection."""
    type: str = Field(default="collections", const=True)
    attributes: CollectionAttributes = Field(description="Collection attributes")
    
    @classmethod
    def create_mock(cls, project_id: str, collection_id: str, name: str, **kwargs) -> "Collection":
        """Create a mock collection for testing."""
        full_id = f"{project_id}/{collection_id}"
        
        attributes = CollectionAttributes(
            id=collection_id,
            name=name,
            description=Description(
                type="text/plain",
                value=kwargs.get("description", f"Description for {name}")
            ) if "description" in kwargs else None,
            **{k: v for k, v in kwargs.items() if k not in ["description", "id", "name"]}
        )
        
        return cls(
            id=full_id,
            attributes=attributes,
            links={
                "self": f"/polarion/rest/v1/projects/{project_id}/collections/{collection_id}",
                "portal": f"/polarion/#/project/{project_id}/collection?id={collection_id}"
            }
        )