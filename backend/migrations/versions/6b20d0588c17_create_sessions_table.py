"""create sessions table

Revision ID: 6b20d0588c17
Revises: 20261026_create_users
Create Date: 2026-10-26 07:03:46.768418

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6b20d0588c17"
down_revision: str | Sequence[str] | None = "20261026_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480",
            name="ck_sessions_duration_minutes",
        ),
        sa.CheckConstraint("capacity BETWEEN 1 AND 100", name="ck_sessions_capacity"),
        sa.CheckConstraint(
            "status IN ('scheduled', 'cancelled')",
            name="ck_sessions_status",
        ),
    )
    op.create_index(
        "ix_sessions_host_starts",
        "sessions",
        ["host_id", "starts_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_host_starts", table_name="sessions")
    op.drop_table("sessions")
