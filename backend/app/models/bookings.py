"""SQLAlchemy model for bookings."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

STATUS_CONFIRMED = "confirmed"
STATUS_WAITLISTED = "waitlisted"
STATUS_CHECKED_IN = "checked_in"
STATUS_CANCELLED = "cancelled"
ACTIVE_STATUSES = (STATUS_CONFIRMED, STATUS_WAITLISTED, STATUS_CHECKED_IN)
OCCUPIED_STATUSES = (STATUS_CONFIRMED, STATUS_CHECKED_IN)


class Booking(Base):
    """A guest's booking for one session."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('confirmed', 'waitlisted', 'cancelled', 'checked_in')",
            name="ck_bookings_status",
        ),
        Index(
            "uq_bookings_active_user_session",
            "session_id",
            "user_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
        Index(
            "ix_bookings_session_status_created",
            "session_id",
            "status",
            "created_at",
        ),
        Index("ix_bookings_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
