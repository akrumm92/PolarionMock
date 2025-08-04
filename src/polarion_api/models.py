"""
Pydantic models for Polarion API data structures.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# Base models for JSON:API structure

class Link(BaseModel):
    """JSON:API link object."""
    href: str


class Links(BaseModel):
    """JSON:API links object."""
    self: Optional[Link] = None
    first: Optional[Link] = None
    last: Optional[Link] = None
    prev: Optional[Link] = None
    next: Optional[Link] = None
    related: Optional[Link] = None


class ResourceIdentifier(BaseModel):
    """JSON:API resource identifier."""
    type: str
    id: str


class Relationship(BaseModel):
    """JSON:API relationship object."""
    data: Optional[Union[ResourceIdentifier, List[ResourceIdentifier]]] = None
    links: Optional[Links] = None


class TextContent(BaseModel):
    """Text content with type."""
    type: str = Field(default="text/plain", description="Content type (text/plain, text/html)")
    value: str = Field(description="Text content value")


# Work Item models

class WorkItemAttributes(BaseModel):
    """Work item attributes."""
    model_config = ConfigDict(extra="allow")
    
    title: str
    type: str = Field(description="Work item type (requirement, task, etc.)")
    description: Optional[TextContent] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    dueDate: Optional[str] = None
    initialEstimate: Optional[str] = None
    remainingEstimate: Optional[str] = None
    timeSpent: Optional[str] = None
    resolution: Optional[str] = None
    resolvedOn: Optional[datetime] = None
    
    # Hyperlinks
    hyperlinks: Optional[List[Dict[str, str]]] = None
    
    # Custom fields (flexible)
    customFields: Optional[Dict[str, Any]] = None


class WorkItemRelationships(BaseModel):
    """Work item relationships."""
    model_config = ConfigDict(extra="allow")
    
    author: Optional[Relationship] = None
    assignee: Optional[Relationship] = None
    project: Optional[Relationship] = None
    module: Optional[Relationship] = None
    parent: Optional[Relationship] = None
    children: Optional[Relationship] = None
    linkedWorkItems: Optional[Relationship] = None
    attachments: Optional[Relationship] = None
    comments: Optional[Relationship] = None


class WorkItem(BaseModel):
    """Work item resource."""
    type: str = Field(default="workitems")
    id: str
    attributes: WorkItemAttributes
    relationships: Optional[WorkItemRelationships] = None
    links: Optional[Links] = None


class WorkItemCreate(BaseModel):
    """Work item creation request."""
    type: str = Field(default="workitems")
    attributes: WorkItemAttributes
    relationships: Optional[WorkItemRelationships] = None


class WorkItemUpdate(BaseModel):
    """Work item update request."""
    type: str = Field(default="workitems")
    id: str
    attributes: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, Any]] = None


# Document models

class DocumentAttributes(BaseModel):
    """Document attributes."""
    model_config = ConfigDict(extra="allow")
    
    title: str
    name: Optional[str] = None
    type: Optional[str] = None
    moduleName: Optional[str] = None
    moduleFolder: Optional[str] = None
    homePageContent: Optional[TextContent] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    status: Optional[str] = None
    structureLink: Optional[bool] = None
    
    # Custom fields
    customFields: Optional[Dict[str, Any]] = None


class DocumentRelationships(BaseModel):
    """Document relationships."""
    model_config = ConfigDict(extra="allow")
    
    project: Optional[Relationship] = None
    author: Optional[Relationship] = None
    updatedBy: Optional[Relationship] = None
    parentDocument: Optional[Relationship] = None
    childDocuments: Optional[Relationship] = None
    headWorkItem: Optional[Relationship] = None


class Document(BaseModel):
    """Document resource."""
    type: str = Field(default="documents")
    id: str
    attributes: DocumentAttributes
    relationships: Optional[DocumentRelationships] = None
    links: Optional[Links] = None


class DocumentCreate(BaseModel):
    """Document creation request."""
    type: str = Field(default="documents")
    attributes: DocumentAttributes
    relationships: Optional[DocumentRelationships] = None


# Project models

class ProjectAttributes(BaseModel):
    """Project attributes."""
    model_config = ConfigDict(extra="allow")
    
    name: str
    id: str
    description: Optional[TextContent] = None
    trackerPrefix: Optional[str] = None
    created: Optional[datetime] = None
    active: Optional[bool] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class Project(BaseModel):
    """Project resource."""
    type: str = Field(default="projects")
    id: str
    attributes: ProjectAttributes
    links: Optional[Links] = None


# API Response models

class Meta(BaseModel):
    """API response metadata."""
    totalCount: Optional[int] = None
    currentPage: Optional[int] = None
    pageSize: Optional[int] = None
    totalPages: Optional[int] = None


class Error(BaseModel):
    """API error object."""
    status: str
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[Dict[str, Any]] = None


class SingleResourceResponse(BaseModel):
    """Single resource response."""
    data: Union[WorkItem, Document, Project]
    included: Optional[List[Dict[str, Any]]] = None
    links: Optional[Links] = None
    meta: Optional[Meta] = None


class CollectionResponse(BaseModel):
    """Collection response."""
    data: List[Union[WorkItem, Document, Project]]
    included: Optional[List[Dict[str, Any]]] = None
    links: Optional[Links] = None
    meta: Optional[Meta] = None


class ErrorResponse(BaseModel):
    """Error response."""
    errors: List[Error]


# Request models

class CreateRequest(BaseModel):
    """Generic create request."""
    data: List[Union[WorkItemCreate, DocumentCreate]]


class UpdateRequest(BaseModel):
    """Generic update request."""
    data: Union[WorkItemUpdate, Dict[str, Any]]


# Query parameters

class QueryParams(BaseModel):
    """Common query parameters."""
    page_size: Optional[int] = Field(None, alias="page[size]")
    page_number: Optional[int] = Field(None, alias="page[number]")
    include: Optional[str] = None
    fields: Optional[Dict[str, str]] = None
    sort: Optional[str] = None
    query: Optional[str] = None