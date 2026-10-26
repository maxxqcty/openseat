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


class RosterEntry(BaseModel):
    """One guest on the host's roster; never includes email addresses."""

    booking_id: uuid.UUID
    display_name: str
    status: str
    created_at: datetime
    checked_in_at: datetime | None = None
    waitlist_position: int | None = None


class Roster(BaseModel):
    """The host's roster grouped by booking status."""

    confirmed: list[RosterEntry]
    waitlisted: list[RosterEntry]
    checked_in: list[RosterEntry]
