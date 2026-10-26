"""create sessions table

Revision ID: 6b20d0588c17
Revises: 20261026_create_users
Create Date: 2026-10-26 07:03:46.768418

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6b20d0588c17'
down_revision: Union[str, Sequence[str], None] = '20261026_create_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("host_id", sa.Integer, nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default=sa.text("60")),
        sa.Column("capacity", sa.Integer, nullable=False, server_default=sa.text("10")),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("scheduled")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("sessions")