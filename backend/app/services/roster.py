"""Host roster and check-in domain logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.errors import ApiError
from app.models.bookings import (
    ACTIVE_STATUSES,
    STATUS_CHECKED_IN,
    STATUS_CONFIRMED,
    STATUS_WAITLISTED,
    Booking,
)
from app.models.sessions import Session
from app.models.users import User
from app.services.bookings import waitlist_positions
from app.services.sessions import as_utc, require_host, utc_now

CHECK_IN_WINDOW_BEFORE_START = timedelta(hours=2)


@dataclass(frozen=True)
class RosterRow:
    """One guest on the roster with their display name and waitlist position."""

    booking: Booking
    display_name: str
    waitlist_position: int | None


@dataclass(frozen=True)
class RosterData:
    """The roster grouped and ordered for the host."""

    confirmed: list[RosterRow]
    waitlisted: list[RosterRow]
    checked_in: list[RosterRow]


def check_in_window(session: Session) -> tuple[datetime, datetime]:
    """Return the inclusive check-in window for a session, in UTC."""
    starts_at = as_utc(session.starts_at)
    opens_at = starts_at - CHECK_IN_WINDOW_BEFORE_START
    closes_at = starts_at + timedelta(minutes=session.duration_minutes)
    return opens_at, closes_at


def is_check_in_open(session: Session, *, now: datetime | None = None) -> bool:
    """Return whether check-in is open from two hours before start until the end."""
    current = now or utc_now()
    opens_at, closes_at = check_in_window(session)
    return opens_at <= current <= closes_at


def get_roster(
    db: DbSession,
    *,
    session_id: uuid.UUID,
    host_id: uuid.UUID,
) -> RosterData:
    """Return the host's roster in one query per group source, never per guest."""
    session = db.get(Session, session_id)
    if session is None:
        raise ApiError(404, "not_found", "Session not found")
    require_host(session, host_id)

    rows = db.execute(
        select(Booking, User.display_name)
        .join(User, Booking.user_id == User.id)
        .where(
            Booking.session_id == session_id,
            Booking.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Booking.created_at.asc(), Booking.id.asc()),
    ).all()
    positions = waitlist_positions(db, [booking for booking, _ in rows])

    confirmed: list[RosterRow] = []
    waitlisted: list[RosterRow] = []
    checked_in: list[RosterRow] = []
    for booking, display_name in rows:
        row = RosterRow(
            booking=booking,
            display_name=display_name,
            waitlist_position=positions.get(booking.id),
        )
        if booking.status == STATUS_CONFIRMED:
            confirmed.append(row)
        elif booking.status == STATUS_WAITLISTED:
            waitlisted.append(row)
        elif booking.status == STATUS_CHECKED_IN:
            checked_in.append(row)

    waitlisted.sort(key=lambda row: row.waitlist_position or 0)
    checked_in.sort(
        key=lambda row: (row.booking.checked_in_at or row.booking.created_at, row.booking.id),
    )
    return RosterData(
        confirmed=confirmed,
        waitlisted=waitlisted,
        checked_in=checked_in,
    )


def check_in_booking(
    db: DbSession,
    *,
    booking_id: uuid.UUID,
    host_id: uuid.UUID,
    now: datetime | None = None,
) -> Booking:
    """Check in a confirmed guest during the check-in window. Host-only."""
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise ApiError(404, "not_found", "Booking not found")

    session = db.scalar(
        select(Session).where(Session.id == booking.session_id).with_for_update(),
    )
    if session is None:
        raise ApiError(404, "not_found", "Booking not found")
    require_host(session, host_id)
    db.refresh(booking)

    if booking.status == STATUS_CHECKED_IN:
        return booking
    if booking.status != STATUS_CONFIRMED:
        raise ApiError(409, "conflict", "Only confirmed bookings can be checked in")

    current = now or utc_now()
    if not is_check_in_open(session, now=current):
        raise ApiError(409, "conflict", "Check-in is not open for this session")

    booking.status = STATUS_CHECKED_IN
    booking.checked_in_at = current
    db.commit()
    db.refresh(booking)
    return booking
