"""Booking API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models.bookings import Booking
from app.models.sessions import Session
from app.models.users import User
from app.schemas.bookings import BookingPublic
from app.schemas.sessions import MyBookingPublic, SessionPublic
from app.services import bookings as booking_service
from app.services.bookings import book_session
from app.services.sessions import is_past

router = APIRouter(prefix="/api/sessions", tags=["bookings"])
me_router = APIRouter(prefix="/api/me", tags=["bookings"])
delete_router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def _my_booking(
    booking: Booking,
    session: Session,
    position: int | None,
) -> MyBookingPublic:
    """Combine a booking with its session summary and waitlist position."""
    booking_payload = BookingPublic.model_validate(booking).model_copy(
        update={"waitlist_position": position},
    )
    session_payload = SessionPublic.model_validate(session).model_copy(
        update={"past": is_past(session)},
    )
    return MyBookingPublic(**booking_payload.model_dump(), session=session_payload)


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


@delete_router.delete(
    "/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_booking(
    booking_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> None:
    """Cancel the caller's booking, promoting the oldest waiter if a seat frees."""
    booking_service.cancel_booking(db, booking_id=booking_id, user_id=user.id)


@me_router.get("/bookings", response_model=list[MyBookingPublic])
def list_my_bookings(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[MyBookingPublic]:
    """Return every booking for the caller, soonest session first."""
    rows = booking_service.list_bookings_for_user(db, user.id)
    positions = booking_service.waitlist_positions(db, [booking for booking, _ in rows])
    return [
        _my_booking(booking, session, positions.get(booking.id))
        for booking, session in rows
    ]
