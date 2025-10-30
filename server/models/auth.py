"""Authentication models for multi-user support."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model for authentication."""
    
    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    provider: str = Field(..., description="OAuth provider (google, github, etc.)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="User creation timestamp")
    
    class Config:
        from_attributes = True


class OAuthState(BaseModel):
    """OAuth state for CSRF protection."""
    
    state: str = Field(..., description="Random state string")
    redirect_uri: str = Field(..., description="Redirect URI after OAuth")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="State creation timestamp")


class TokenData(BaseModel):
    """JWT token payload data."""
    
    user_id: str = Field(..., description="User ID from token")
    email: str = Field(..., description="User email from token")
    exp: datetime = Field(..., description="Token expiration time")


class UserCreate(BaseModel):
    """Model for creating a new user."""
    
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    provider: str = Field(..., description="OAuth provider")


class UserResponse(BaseModel):
    """User response model (excludes sensitive data)."""
    
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    provider: str = Field(..., description="OAuth provider")
    created_at: datetime = Field(..., description="User creation timestamp")


__all__ = ["User", "OAuthState", "TokenData", "UserCreate", "UserResponse"]

