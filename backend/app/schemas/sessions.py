"""Pydantic models for session API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Input for creating a new session."""

    title: str = Field(min_length=1, description="Session title")
    description: str | None = Field(default=None, description="Optional session description")
    start_at: datetime = Field(description="Session start time (UTC ISO 8601)")
    duration_minutes: int = Field(default=60, ge=1, description="Duration in minutes")
    capacity: int = Field(default=10, ge=1, description="Maximum attendees")
    location: str | None = Field(default=None, description="Optional session location")


class SessionPublic(BaseModel):
    """Public-facing session data returned to all users."""

    id: int
    host_id: int
    title: str
    description: str | None = None
    start_at: datetime
    duration_minutes: int
    capacity: int
    location: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def my_booking(self):
        """Placeholder for the signed-in user's booking (set by routes)."""
        return None


class SessionUpdate(BaseModel):
    """Partial update for a session (out of scope for issue #5)."""

    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None)
    start_at: datetime | None = Field(default=None)
    duration_minutes: int | None = Field(default=None, ge=1)
    capacity: int | None = Field(default=None, ge=1)
    location: str | None = Field(default=None)
    status: str | None = Field(default=None)