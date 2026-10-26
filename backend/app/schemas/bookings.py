"""Pydantic models for booking requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    """Input for creating a booking."""

    session_id: int = Field(..., gt=0, description="Session ID to book")


class BookingResponse(BaseModel):
    """Public-facing booking response."""

    status: str = Field(description="Booking status: confirmed or waitlisted")
    booking_id: int = Field(..., gt=0, description="Generated booking ID")
    session_id: int = Field(..., gt=0, description="Session ID")
    user_id: int = Field(..., gt=0, description="User ID who made the booking")

    model_config = {"from_attributes": True}