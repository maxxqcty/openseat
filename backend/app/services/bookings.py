"""Race-safe booking service with row-level locking and capacity enforcement.

Constraints (from issue #6):
- Use SELECT ... FOR UPDATE on the session row inside one transaction.
- Never count seats outside the locked transaction.
- Include checked_in in the occupied count from the start.
- The invariant confirmed + checked_in <= capacity holds after every commit.
- Return documented error shapes; no bare exception strings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.config import get_db_session
from app.models.sessions import Session as SessionModel
from app.models.bookings import Booking

STATUS_CONFIRMED = "confirmed"
STATUS_WAITLISTED = "waitlisted"
STATUS_CANCELLED = "cancelled"

ERROR_SESSION_NOT_FOUND = "Session not found"
ERROR_SESSION_ENDED = "Cannot book an ended session"
ERROR_BOOKING_CONFLICT = "Booking conflict: user already has an active booking"


def _count_occupied(db, session: SessionModel) -> int:
    """Count confirmed + checked_in bookings for a session inside a locked transaction.

    This must be called while the session row is locked via FOR UPDATE.
    """
    stmt = select(func.count(Booking.id)).where(
        Booking.session_id == session.id,
        Booking.status == STATUS_CONFIRMED,
    )
    confirmed = db.execute(stmt).scalar_one()

    stmt2 = select(func.count(Booking.id)).where(
        Booking.session_id == session.id,
        Booking.status == STATUS_CONFIRMED,
        Booking.checked_in,
    )
    checked_in = db.execute(stmt2).scalar_one()

    return confirmed + checked_in


def book_session(session_id: int, user_id: int) -> dict:
    """Book a seat in a session with race-safe capacity enforcement.

    Returns a dict with:
        {
            "status": "confirmed" | "waitlisted",
            "booking_id": int,
            "session_id": int,
            "user_id": int,
        }

    Raises ValueError for:
        - Session not found
        - Session ended/cancelled
        - User already has active booking (unique index violation)
    """
    db = next(get_db_session())
    try:
        # Lock the session row with FOR UPDATE to prevent concurrent races
        stmt = select(SessionModel).where(SessionModel.id == session_id).with_for_update()
        session = db.scalar(stmt)
        if not session:
            raise ValueError(ERROR_SESSION_NOT_FOUND)

        # If session is past or cancelled, reject
        now = datetime.now(timezone.utc)
        if now > session.start_at + timedelta(minutes=session.duration_minutes) or session.status == STATUS_CANCELLED:
            raise ValueError(ERROR_SESSION_ENDED)

        # Count occupied seats while the row is locked
        occupied = _count_occupied(db, session)

        if occupied >= session.capacity:
            # Session is full -> waitlisted
            booking = Booking(
                session_id=session.id,
                user_id=user_id,
                status=STATUS_WAITLISTED,
                checked_in=False,
                created_at=now,
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return {
                "status": STATUS_WAITLISTED,
                "booking_id": booking.id,
                "session_id": session.id,
                "user_id": user_id,
            }
        else:
            # Seat available -> confirmed
            booking = Booking(
                session_id=session.id,
                user_id=user_id,
                status=STATUS_CONFIRMED,
                checked_in=False,
                created_at=now,
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return {
                "status": STATUS_CONFIRMED,
                "booking_id": booking.id,
                "session_id": session.id,
                "user_id": user_id,
            }
    except ValueError as e:
        db.rollback()
        raise e
    except IntegrityError:
        # Unique index violation: user already has an active (non-cancelled) booking
        db.rollback()
        raise ValueError(ERROR_BOOKING_CONFLICT)
    finally:
        db.close()