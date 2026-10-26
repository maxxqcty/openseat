"""Pydantic models for session API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bookings import BookingPublic


class SessionCreate(BaseModel):
    """Input for creating a new session."""

    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    starts_at: datetime
    duration_minutes: int = Field(ge=15, le=480)
    capacity: int = Field(ge=1, le=100)
    location: str = Field(min_length=3, max_length=200)


class SessionPublic(BaseModel):
    """Session fields safe to expose to everyone."""

    id: uuid.UUID
    host_id: uuid.UUID
    title: str
    description: str
    starts_at: datetime
    duration_minutes: int
    capacity: int
    location: str
    status: str
    created_at: datetime
    past: bool = False

    model_config = ConfigDict(from_attributes=True)


class SessionDetail(SessionPublic):
    """Session detail with seat counts and the caller's booking."""

    confirmed_count: int
    checked_in_count: int
    waitlist_count: int
    my_booking: BookingPublic | None = None
