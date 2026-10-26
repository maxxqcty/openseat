"""SQLAlchemy model for workshop sessions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

STATUS_SCHEDULED = "scheduled"
STATUS_CANCELLED = "cancelled"
STATUSES = (STATUS_SCHEDULED, STATUS_CANCELLED)


class Session(Base):
    """A one-off workshop published by a host."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480",
            name="ck_sessions_duration_minutes",
        ),
        CheckConstraint("capacity BETWEEN 1 AND 100", name="ck_sessions_capacity"),
        CheckConstraint(
            "status IN ('scheduled', 'cancelled')",
            name="ck_sessions_status",
        ),
        Index("ix_sessions_host_starts", "host_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=STATUS_SCHEDULED,
        server_default=STATUS_SCHEDULED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
