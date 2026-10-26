"""SQLAlchemy 2 models for booking records."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.models.base import Base


class Booking(Base):
    """Database model for session bookings."""

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(String(32), nullable=False)
    checked_in = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False)