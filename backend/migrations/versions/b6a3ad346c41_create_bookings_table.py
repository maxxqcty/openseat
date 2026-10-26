"""create bookings table

Revision ID: b6a3ad346c41
Revises: 6b20d0588c17
Create Date: 2026-10-26 07:29:24.254778
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b6a3ad346c41'
down_revision: Union[str, Sequence[str], None] = '6b20d0588c17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("session_id", sa.Integer, nullable=False, index=True),
        sa.Column("user_id", sa.Integer, nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("checked_in", sa.Boolean, default=False, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    # Partial unique index: one active (non-cancelled) booking per user+session
    op.create_index(
        "ix_bookings_user_session_active",
        "bookings",
        ["user_id", "session_id"],
        unique=True,
        postgresql_where="status != 'cancelled'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_bookings_user_session_active", table_name="bookings")
    op.drop_table("bookings")