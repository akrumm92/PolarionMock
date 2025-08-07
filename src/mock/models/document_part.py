"""
Document Part model for Polarion Mock Server.

Implements the Document Parts API for managing WorkItems within documents.
"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class DocumentPart(BaseModel):
    """Document Part model representing a part within a Polarion document.
    
    This model tracks WorkItems that have been added to documents via the
    Document Parts API. Without this, WorkItems remain in the "Recycle Bin".
    """
    
    id: str = Field(description="Document part ID (e.g., 'Python/SpaceId/DocumentName/workitem_PYTH-1234')")
    type: Literal["document_parts"] = Field(default="document_parts")
    part_type: str = Field(description="Type of part (workitem or heading)")
    workitem_id: Optional[str] = Field(default=None, description="Reference to WorkItem")
    position: int = Field(description="Order position in document")
    previous_part_id: Optional[str] = Field(default=None, description="ID of previous part for positioning")
    
    # Tracking fields
    document_id: str = Field(description="Full document ID (project/space/document)")
    created_at: str = Field(description="When the part was added to document")
    
    def to_json_api(self) -> Dict[str, Any]:
        """Convert to JSON:API format."""
        data = {
            "type": self.type,
            "id": self.id,
            "links": {
                "self": f"/polarion/rest/v1/parts/{self.id}"
            }
        }
        
        # Add attributes if needed (Polarion typically doesn't return these)
        if self.part_type == "workitem" and self.workitem_id:
            data["relationships"] = {
                "workItem": {
                    "data": {
                        "type": "workitems",
                        "id": self.workitem_id
                    }
                }
            }
        
        return data
    
    @classmethod
    def create_workitem_part(cls, document_id: str, workitem_id: str, position: int,
                            previous_part_id: Optional[str] = None) -> "DocumentPart":
        """Create a document part for a WorkItem.
        
        Args:
            document_id: Full document ID (project/space/document)
            workitem_id: Full WorkItem ID (project/ITEM-123)
            position: Position in document
            previous_part_id: Optional ID of part to insert after
        """
        from datetime import datetime
        
        # Extract the short WorkItem ID for the part ID
        short_wi_id = workitem_id.split("/")[-1] if "/" in workitem_id else workitem_id
        
        part_id = f"{document_id}/workitem_{short_wi_id}"
        
        return cls(
            id=part_id,
            part_type="workitem",
            workitem_id=workitem_id,
            position=position,
            previous_part_id=previous_part_id,
            document_id=document_id,
            created_at=datetime.utcnow().isoformat()
        )


class RecycleBin:
    """Track WorkItems in Recycle Bin state (have module but not in document).
    
    This is a mock-specific utility to track WorkItems that have been created
    with a module relationship but haven't been added to the document via
    the Document Parts API.
    """
    
    def __init__(self):
        self.items: Dict[str, Any] = {}  # workitem_id -> WorkItem
    
    def add(self, workitem):
        """Add WorkItem to recycle bin if it has module but not in document."""
        if hasattr(workitem, "relationships") and workitem.relationships:
            module = workitem.relationships.get("module", {})
            if module and hasattr(workitem, "_is_in_document") and not workitem._is_in_document:
                self.items[workitem.id] = workitem
                if hasattr(workitem, "_in_recycle_bin"):
                    workitem._in_recycle_bin = True
    
    def remove(self, workitem_id: str):
        """Remove WorkItem from recycle bin (when added to document)."""
        if workitem_id in self.items:
            workitem = self.items[workitem_id]
            if hasattr(workitem, "_in_recycle_bin"):
                workitem._in_recycle_bin = False
            del self.items[workitem_id]
    
    def list_for_document(self, document_id: str) -> list:
        """List all WorkItems in recycle bin for a specific document."""
        items = []
        for wi in self.items.values():
            if hasattr(wi, "relationships") and wi.relationships:
                module = wi.relationships.get("module", {})
                if module and module.get("data", {}).get("id") == document_id:
                    items.append(wi)
        return items
    
    def contains(self, workitem_id: str) -> bool:
        """Check if a WorkItem is in the recycle bin."""
        return workitem_id in self.items