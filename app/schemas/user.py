"""User schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Shared properties."""

    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Properties to receive via API on creation."""

    password: str


class UserUpdate(UserBase):
    """Properties to receive via API on update."""

    password: Optional[str] = None


class UserResponse(UserBase):
    """Properties to return via API."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
