"""
User model for Polarion Mock Server
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from .common import BaseResource


class UserAttributes(BaseModel):
    """User attributes following Polarion API specification."""
    id: str = Field(description="User ID")
    name: str = Field(description="User display name")
    email: Optional[str] = Field(default=None, description="User email address")
    description: Optional[str] = Field(default=None, description="User description")
    disabled: bool = Field(default=False, description="Whether user is disabled")
    created: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }


class User(BaseResource):
    """User model representing a Polarion user."""
    type: str = Field(default="users", const=True)
    attributes: UserAttributes = Field(description="User attributes")
    
    @classmethod
    def create_mock(cls, user_id: str, name: Optional[str] = None, **kwargs) -> "User":
        """Create a mock user for testing."""
        if not name:
            name = f"User {user_id}"
        
        attributes = UserAttributes(
            id=user_id,
            name=name,
            email=kwargs.get("email", f"{user_id}@example.com"),
            **{k: v for k, v in kwargs.items() if k not in ["email"]}
        )
        
        return cls(
            id=user_id,
            attributes=attributes,
            links={
                "self": f"/polarion/rest/v1/users/{user_id}",
                "portal": f"/polarion/#/user/{user_id}"
            }
        )