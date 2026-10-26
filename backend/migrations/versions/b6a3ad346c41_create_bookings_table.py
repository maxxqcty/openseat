"""create bookings table

Revision ID: b6a3ad346c41
Revises: 6b20d0588c17
Create Date: 2026-10-26 07:29:24.254778
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b6a3ad346c41"
down_revision: str | Sequence[str] | None = "6b20d0588c17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('confirmed', 'waitlisted', 'cancelled', 'checked_in')",
            name="ck_bookings_status",
        ),
    )
    op.create_index(
        "uq_bookings_active_user_session",
        "bookings",
        ["session_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )
    op.create_index(
        "ix_bookings_session_status_created",
        "bookings",
        ["session_id", "status", "created_at"],
    )
    op.create_index(
        "ix_bookings_user_created",
        "bookings",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_user_created", table_name="bookings")
    op.drop_index("ix_bookings_session_status_created", table_name="bookings")
    op.drop_index("uq_bookings_active_user_session", table_name="bookings")
    op.drop_table("bookings")
