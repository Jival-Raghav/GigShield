"""Add upi_id column to workers table.

Revision ID: 20260402_01
Revises:
Create Date: 2026-04-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260402_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workers", sa.Column("upi_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("workers", "upi_id")
