"""SQLAlchemy 2 models for session bookings."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from .base import Base


class Session(Base):
    """Database model for workshop sessions."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    start_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    capacity = Column(Integer, nullable=False, default=10)
    location = Column(String(256), nullable=True)
    status = Column(String(32), nullable=False, default="scheduled")
    created_at = Column(DateTime, nullable=False, server_default="now()")