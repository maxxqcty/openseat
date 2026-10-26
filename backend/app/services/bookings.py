"""Race-safe booking logic with capacity enforcement."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.errors import ApiError
from app.models.bookings import (
    OCCUPIED_STATUSES,
    STATUS_CONFIRMED,
    STATUS_WAITLISTED,
    Booking,
)
from app.models.sessions import STATUS_CANCELLED as SESSION_CANCELLED
from app.models.sessions import Session
from app.services.sessions import is_past, utc_now


def status_for_occupancy(*, occupied: int, capacity: int) -> str:
    """Return the booking status for a session with ``occupied`` seats taken."""
    return STATUS_WAITLISTED if occupied >= capacity else STATUS_CONFIRMED


def count_occupied(db: DbSession, session_id: uuid.UUID) -> int:
    """Count bookings that occupy a seat (confirmed plus checked in)."""
    count = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.session_id == session_id,
            Booking.status.in_(OCCUPIED_STATUSES),
        ),
    )
    return int(count or 0)


def waitlist_position(db: DbSession, booking: Booking) -> int | None:
    """Return the 1-based waitlist position for a waitlisted booking."""
    if booking.status != STATUS_WAITLISTED:
        return None

    waitlisted_ids = list(
        db.scalars(
            select(Booking.id)
            .where(
                Booking.session_id == booking.session_id,
                Booking.status == STATUS_WAITLISTED,
            )
            .order_by(Booking.created_at.asc(), Booking.id.asc()),
        ).all(),
    )
    try:
        return waitlisted_ids.index(booking.id) + 1
    except ValueError:
        return None


def book_session(
    db: DbSession,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[Booking, int | None]:
    """Book a seat or the waitlist under a row lock on the session.

    The session row is locked with ``SELECT ... FOR UPDATE`` before the seat
    count, so concurrent requests serialise and the invariant
    ``confirmed + checked_in <= capacity`` holds at every commit.
    """
    session = db.scalar(
        select(Session).where(Session.id == session_id).with_for_update(),
    )
    if session is None:
        raise ApiError(404, "not_found", "Session not found")
    if session.status == SESSION_CANCELLED or is_past(session):
        raise ApiError(409, "conflict", "This session is not open for booking")

    occupied = count_occupied(db, session.id)
    status = status_for_occupancy(occupied=occupied, capacity=session.capacity)
    created_at: datetime = utc_now()

    booking = Booking(
        session_id=session.id,
        user_id=user_id,
        status=status,
        created_at=created_at,
    )
    db.add(booking)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "booking_conflict",
            "You already have an active booking for this session",
        ) from exc

    position = waitlist_position(db, booking)
    db.commit()
    db.refresh(booking)
    return booking, position
