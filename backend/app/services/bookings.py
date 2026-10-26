"""Race-safe booking logic with capacity enforcement."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.errors import ApiError
from app.models.bookings import (
    OCCUPIED_STATUSES,
    STATUS_CANCELLED,
    STATUS_CHECKED_IN,
    STATUS_CONFIRMED,
    STATUS_WAITLISTED,
    Booking,
)
from app.models.sessions import STATUS_CANCELLED as SESSION_CANCELLED
from app.models.sessions import Session
from app.services.sessions import is_past, utc_now

logger = logging.getLogger(__name__)


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


def waitlist_order() -> list[Any]:
    """Return the deterministic oldest-first ordering for the waitlist."""
    return [Booking.created_at.asc(), Booking.id.asc()]


def waitlist_positions(
    db: DbSession,
    bookings: Sequence[Booking],
) -> dict[uuid.UUID, int]:
    """Return 1-based waitlist positions for the given bookings in one query."""
    waitlisted = [booking for booking in bookings if booking.status == STATUS_WAITLISTED]
    if not waitlisted:
        return {}

    session_ids = {booking.session_id for booking in waitlisted}
    ranked = (
        select(
            Booking.id.label("booking_id"),
            func.row_number()
            .over(
                partition_by=Booking.session_id,
                order_by=waitlist_order(),
            )
            .label("position"),
        )
        .where(
            Booking.session_id.in_(session_ids),
            Booking.status == STATUS_WAITLISTED,
        )
        .subquery()
    )
    rows = db.execute(
        select(ranked.c.booking_id, ranked.c.position).where(
            ranked.c.booking_id.in_([booking.id for booking in waitlisted]),
        ),
    ).all()
    return {booking_id: int(position) for booking_id, position in rows}


def waitlist_position(db: DbSession, booking: Booking) -> int | None:
    """Return the 1-based waitlist position for a waitlisted booking."""
    if booking.status != STATUS_WAITLISTED:
        return None
    return waitlist_positions(db, [booking]).get(booking.id)


def list_bookings_for_user(
    db: DbSession,
    user_id: uuid.UUID,
) -> list[tuple[Booking, Session]]:
    """Return every booking for a user with its session, soonest first."""
    rows = db.execute(
        select(Booking, Session)
        .join(Session, Booking.session_id == Session.id)
        .where(Booking.user_id == user_id)
        .order_by(
            Session.starts_at.asc(),
            Booking.created_at.asc(),
            Booking.id.asc(),
        ),
    ).all()
    return [(booking, session) for booking, session in rows]


def _promote_oldest_waiter(
    db: DbSession,
    session_id: uuid.UUID,
    *,
    now: datetime,
) -> Booking | None:
    """Move the oldest waitlisted booking to confirmed, if any."""
    promoted = db.scalar(
        select(Booking)
        .where(
            Booking.session_id == session_id,
            Booking.status == STATUS_WAITLISTED,
        )
        .order_by(*waitlist_order())
        .limit(1)
        .with_for_update(),
    )
    if promoted is None:
        return None
    promoted.status = STATUS_CONFIRMED
    promoted.promoted_at = now
    return promoted


def cancel_booking(
    db: DbSession,
    *,
    booking_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Cancel the caller's booking and promote the oldest waiter if a seat frees."""
    booking = db.get(Booking, booking_id)
    if booking is None or booking.user_id != user_id:
        raise ApiError(404, "not_found", "Booking not found")

    session = db.scalar(
        select(Session).where(Session.id == booking.session_id).with_for_update(),
    )
    if session is None:
        raise ApiError(404, "not_found", "Booking not found")
    db.refresh(booking)

    if booking.status == STATUS_CANCELLED:
        return
    if booking.status == STATUS_CHECKED_IN:
        raise ApiError(409, "conflict", "Checked-in bookings cannot be cancelled")

    now = utc_now()
    freed_seat = booking.status == STATUS_CONFIRMED
    booking.status = STATUS_CANCELLED
    booking.cancelled_at = now

    if freed_seat:
        promoted = _promote_oldest_waiter(db, session.id, now=now)
        if promoted is not None:
            logger.info(
                "waitlist_promoted",
                extra={
                    "session_id": str(session.id),
                    "booking_id": str(promoted.id),
                },
            )

    db.commit()


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
