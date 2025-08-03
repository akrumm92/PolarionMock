"""
Common data models used across Polarion Mock Server
"""

from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class Description(BaseModel):
    """Description field with type and value."""
    type: str = Field(default="text/plain", description="Content type (text/plain or text/html)")
    value: str = Field(description="Description content")


class Link(BaseModel):
    """Link object for relationships."""
    href: str = Field(description="URL of the link")
    rel: Optional[str] = Field(default=None, description="Relationship type")
    type: Optional[str] = Field(default=None, description="Media type")
    title: Optional[str] = Field(default=None, description="Link title")


class Error(BaseModel):
    """Error object following JSON:API specification."""
    status: str = Field(description="HTTP status code")
    title: str = Field(description="Error title")
    detail: Optional[str] = Field(default=None, description="Error details")
    source: Optional[Dict[str, Any]] = Field(default=None, description="Error source")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class Meta(BaseModel):
    """Metadata object."""
    totalCount: Optional[int] = Field(default=None, description="Total count for collections")
    pageCount: Optional[int] = Field(default=None, description="Items on current page")
    currentPage: Optional[int] = Field(default=None, description="Current page number")
    pageSize: Optional[int] = Field(default=None, description="Page size")
    totalPages: Optional[int] = Field(default=None, description="Total pages")
    errors: Optional[List[Error]] = Field(default=None, description="Non-fatal errors")


class Revision(BaseModel):
    """Revision information."""
    id: str = Field(description="Revision ID")
    created: datetime = Field(description="Revision creation time")
    author: str = Field(description="Revision author")
    message: Optional[str] = Field(default=None, description="Revision message")


class User(BaseModel):
    """User reference."""
    type: Literal["users"] = Field(default="users")
    id: str = Field(description="User ID")
    name: Optional[str] = Field(default=None, description="User display name")
    email: Optional[str] = Field(default=None, description="User email")


class BaseResource(BaseModel):
    """Base class for all Polarion resources."""
    type: str = Field(description="Resource type")
    id: str = Field(description="Resource ID")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Resource attributes")
    relationships: Optional[Dict[str, Any]] = Field(default=None, description="Related resources")
    links: Optional[Dict[str, str]] = Field(default=None, description="Resource links")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
    
    def to_json_api(self) -> Dict[str, Any]:
        """Convert to JSON:API format."""
        data = {
            "type": self.type,
            "id": self.id
        }
        
        if self.attributes:
            data["attributes"] = self.attributes
        
        if self.relationships:
            data["relationships"] = self.relationships
        
        if self.links:
            data["links"] = self.links
        
        if self.meta:
            data["meta"] = self.meta
        
        return data