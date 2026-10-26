"""Booking API routes with race-safe capacity enforcement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException

from app.services.bookings import book_session
from app.services.sessions import get_session
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/sessions/{session_id}/bookings", tags=["bookings"])


@router.post("/", status_code=201, response_model=dict)
async def create_booking(
    session_id: int,
    request: Request,
) -> dict:
    """Book a seat in a session.

    Returns 201 with ``status: "confirmed"`` when a seat is free,
    or 201 with ``status: "waitlisted"`` when the session is full.

    A second active booking by the same user returns 409.
    Booking a cancelled or ended session returns 409.

    The booking transaction locks the session row with FOR UPDATE,
    counts confirmed + checked_in, and commits before releasing the lock.
    """
    user = await get_current_user(request)
    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Check if session is ended or cancelled
    now = datetime.now(timezone.utc)
    if now > session.start_at + timedelta(minutes=session.duration_minutes):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot book an ended session",
        )
    if session.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot book a cancelled session",
        )

    try:
        result = book_session(session_id, user.id)
    except ValueError as e:
        if "Session not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        if "Cannot book an ended session" in str(e) or "Cannot book a cancelled session" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        if "Booking conflict" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Booking conflict: user already has an active booking",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return result