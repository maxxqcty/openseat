"""Pydantic models for bookings."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookingPublic(BaseModel):
    """A booking as returned by the API."""

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime
    promoted_at: datetime | None = None
    checked_in_at: datetime | None = None
    cancelled_at: datetime | None = None
    waitlist_position: int | None = None

    model_config = ConfigDict(from_attributes=True)
