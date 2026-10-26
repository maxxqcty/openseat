"""Booking API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models.users import User
from app.schemas.bookings import BookingPublic
from app.services.bookings import book_session

router = APIRouter(prefix="/api/sessions", tags=["bookings"])


@router.post(
    "/{session_id}/bookings",
    status_code=status.HTTP_201_CREATED,
    response_model=BookingPublic,
)
def create_booking(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> BookingPublic:
    """Book a seat, or join the waitlist when the session is full."""
    booking, position = book_session(
        db,
        session_id=session_id,
        user_id=user.id,
    )
    return BookingPublic.model_validate(booking).model_copy(
        update={"waitlist_position": position},
    )
