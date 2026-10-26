"""Pydantic models for authentication."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Input for creating an account."""

    display_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Input for signing in."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    """Public user representation; never includes the password hash."""

    id: uuid.UUID
    email: str
    display_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
