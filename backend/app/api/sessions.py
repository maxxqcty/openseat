"""Session API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user, get_optional_user
from app.db import get_db
from app.models.sessions import Session
from app.models.users import User
from app.schemas.bookings import BookingPublic, Roster, RosterEntry
from app.schemas.sessions import SessionCreate, SessionDetail, SessionPublic
from app.services import roster as roster_service
from app.services import sessions as session_service
from app.services.bookings import waitlist_position

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _build_detail(
    db: DbSession,
    session: Session,
    user: User | None,
) -> SessionDetail:
    counts = session_service.seat_counts(db, session.id)
    mine = (
        session_service.find_my_booking(
            db,
            session_id=session.id,
            user_id=user.id,
        )
        if user is not None
        else None
    )
    my_booking = None
    if mine is not None:
        my_booking = BookingPublic.model_validate(mine).model_copy(
            update={"waitlist_position": waitlist_position(db, mine)},
        )

    return SessionDetail(
        id=session.id,
        host_id=session.host_id,
        title=session.title,
        description=session.description,
        starts_at=session.starts_at,
        duration_minutes=session.duration_minutes,
        capacity=session.capacity,
        location=session.location,
        status=session.status,
        created_at=session.created_at,
        past=session_service.is_past(session),
        confirmed_count=counts[session_service.BOOKING_STATUS_CONFIRMED],
        checked_in_count=counts[session_service.BOOKING_STATUS_CHECKED_IN],
        waitlist_count=counts[session_service.BOOKING_STATUS_WAITLISTED],
        my_booking=my_booking,
    )


@router.get("", response_model=list[SessionPublic])
def list_sessions(
    db: Annotated[DbSession, Depends(get_db)],
) -> list[Session]:
    """List upcoming scheduled sessions."""
    return session_service.list_sessions(db)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SessionPublic)
def create_session(
    payload: SessionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Session:
    """Publish a session with the caller as host."""
    return session_service.create_session(
        db,
        host_id=user.id,
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        duration_minutes=payload.duration_minutes,
        capacity=payload.capacity,
        location=payload.location,
    )


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: uuid.UUID,
    user: Annotated[User | None, Depends(get_optional_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> SessionDetail:
    """Return session detail with seat counts and the caller's booking."""
    session = session_service.get_session(db, session_id)
    return _build_detail(db, session, user)


def _roster_entry(row: roster_service.RosterRow) -> RosterEntry:
    return RosterEntry(
        booking_id=row.booking.id,
        display_name=row.display_name,
        status=row.booking.status,
        created_at=row.booking.created_at,
        checked_in_at=row.booking.checked_in_at,
        waitlist_position=row.waitlist_position,
    )


@router.get("/{session_id}/bookings", response_model=Roster)
def get_roster(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Roster:
    """Return the host's roster grouped into confirmed, waitlisted, and checked in."""
    data = roster_service.get_roster(db, session_id=session_id, host_id=user.id)
    return Roster(
        confirmed=[_roster_entry(row) for row in data.confirmed],
        waitlisted=[_roster_entry(row) for row in data.waitlisted],
        checked_in=[_roster_entry(row) for row in data.checked_in],
    )


@router.post("/{session_id}/cancel", response_model=SessionDetail)
def cancel_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> SessionDetail:
    """Cancel a session and every active booking on it. Host-only."""
    session = session_service.cancel_session(
        db,
        session_id=session_id,
        host_id=user.id,
    )
    return _build_detail(db, session, user)
