"""Session domain logic: creation, listing, detail, and cancellation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session as DbSession

from app.errors import ApiError
from app.models.bookings import ACTIVE_STATUSES, Booking
from app.models.sessions import STATUS_CANCELLED, STATUS_SCHEDULED, Session

BOOKING_STATUS_CONFIRMED = "confirmed"
BOOKING_STATUS_WAITLISTED = "waitlisted"
BOOKING_STATUS_CHECKED_IN = "checked_in"
BOOKING_STATUS_CANCELLED = "cancelled"


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalise a datetime to aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_past(session: Session, *, now: datetime | None = None) -> bool:
    """Derive whether a session has ended from start plus duration."""
    current = now or utc_now()
    ends_at = as_utc(session.starts_at) + timedelta(minutes=session.duration_minutes)
    return current > ends_at


def _not_ended_clause() -> object:
    ends_at = Session.starts_at + func.make_interval(
        0,
        0,
        0,
        0,
        0,
        Session.duration_minutes,
    )
    return ends_at > func.now()


def create_session(
    db: DbSession,
    *,
    host_id: uuid.UUID,
    title: str,
    description: str,
    starts_at: datetime,
    duration_minutes: int,
    capacity: int,
    location: str,
) -> Session:
    """Create a scheduled session with the caller as host."""
    start = as_utc(starts_at)
    if start <= utc_now():
        raise ApiError(422, "validation_error", "starts_at must be in the future")

    session = Session(
        host_id=host_id,
        title=title.strip(),
        description=description.strip(),
        starts_at=start,
        duration_minutes=duration_minutes,
        capacity=capacity,
        location=location.strip(),
        status=STATUS_SCHEDULED,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: DbSession) -> list[Session]:
    """Return scheduled sessions that have not ended, soonest first."""
    statement = (
        select(Session)
        .where(Session.status == STATUS_SCHEDULED, _not_ended_clause())  # type: ignore[arg-type]
        .order_by(Session.starts_at.asc())
    )
    return list(db.scalars(statement).all())


def get_session(db: DbSession, session_id: uuid.UUID) -> Session:
    """Load a session by id or raise 404."""
    session = db.get(Session, session_id)
    if session is None:
        raise ApiError(404, "not_found", "Session not found")
    return session


def seat_counts(db: DbSession, session_id: uuid.UUID) -> dict[str, int]:
    """Return confirmed, checked-in, and waitlisted counts in one query."""
    rows = db.execute(
        select(Booking.status, func.count(Booking.id))
        .where(Booking.session_id == session_id)
        .group_by(Booking.status),
    ).all()
    counts = {
        BOOKING_STATUS_CONFIRMED: 0,
        BOOKING_STATUS_CHECKED_IN: 0,
        BOOKING_STATUS_WAITLISTED: 0,
    }
    for status, count in rows:
        if status in counts:
            counts[status] = count
    return counts


def find_my_booking(
    db: DbSession,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Booking | None:
    """Return the caller's active booking for a session, if any."""
    return db.scalar(
        select(Booking)
        .where(
            Booking.session_id == session_id,
            Booking.user_id == user_id,
            Booking.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Booking.created_at.desc())
        .limit(1),
    )


def cancel_session(
    db: DbSession,
    *,
    session_id: uuid.UUID,
    host_id: uuid.UUID,
) -> Session:
    """Cancel a session and its active bookings. Host-only and idempotent."""
    session = db.scalar(
        select(Session).where(Session.id == session_id).with_for_update(),
    )
    if session is None:
        raise ApiError(404, "not_found", "Session not found")
    if session.host_id != host_id:
        raise ApiError(403, "forbidden", "Only the host can cancel this session")
    if session.status == STATUS_CANCELLED:
        return session

    now = utc_now()
    session.status = STATUS_CANCELLED
    db.execute(
        update(Booking)
        .where(
            Booking.session_id == session_id,
            Booking.status != BOOKING_STATUS_CANCELLED,
        )
        .values(
            status=BOOKING_STATUS_CANCELLED,
            cancelled_at=now,
        ),
    )
    db.commit()
    db.refresh(session)
    return session
