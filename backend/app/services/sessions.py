"""Session service with host-only cancellation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import get_db_session
from app.models.sessions import Session as SessionModel

STATUS_CHOICES = ("scheduled", "cancelled")


def _is_past(session: SessionModel) -> bool:
    """Derived: session has already started (starts_at + duration_minutes)."""
    now = datetime.now(timezone.utc)
    return now > session.start_at + timedelta(minutes=session.duration_minutes)


def create_session(
    host_id: int,
    title: str,
    description: str | None,
    start_at: datetime,
    duration_minutes: int,
    capacity: int,
    location: str | None,
) -> SessionModel:
    """Create a new session with the given host.

    The caller becomes the host. Invalid fields raise ValueError.
    """
    if not title or not title.strip():
        raise ValueError("title is required")
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")

    session = SessionModel(
        host_id=host_id,
        title=title.strip(),
        description=description.strip() if description else None,
        start_at=start_at if start_at.tzinfo else start_at.replace(tzinfo=timezone.utc),
        duration_minutes=duration_minutes,
        capacity=capacity,
        location=location.strip() if location else None,
        status="scheduled",
    )

    db = next(get_db_session())
    try:
        db.add(session)
        db.commit()
        db.refresh(session)
    finally:
        db.close()

    return session


def list_sessions() -> list[SessionModel]:
    """Return all sessions that have not ended, ordered by starts_at ascending."""
    db = next(get_db_session())
    try:
        stmt = select(SessionModel).where(SessionModel.past is False).order_by(
            SessionModel.start_at.asc()
        )
        result = db.execute(stmt)
        return result.scalars().all()
    finally:
        db.close()


def get_session(session_id: int) -> SessionModel | None:
    """Return a session by id, or None if not found."""
    db = next(get_db_session())
    try:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    finally:
        db.close()


def cancel_session(session_id: int, host_id: int) -> bool:
    """Cancel a session and set its status to cancelled.

    Host-only: returns False if host_id does not match the session's host.
    Idempotent: returns True even if already cancelled.
    Returns True on success.
    """
    db = next(get_db_session())
    try:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        session = db.scalar(stmt)
        if not session:
            return False

        # Host-only check (integer comparison)
        if session.host_id != host_id:
            return False

        # Cancel the session status
        session.status = "cancelled"
        db.commit()

        return True
    finally:
        db.close()