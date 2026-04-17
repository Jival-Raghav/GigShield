"""Add persisted fraud explanation fields to claims.

Revision ID: 20260417_01
Revises: 20260402_01
Create Date: 2026-04-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260417_01"
down_revision = "20260402_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("fraud_score", sa.Float(), nullable=True))
    op.add_column("claims", sa.Column("fraud_band", sa.String(length=16), nullable=True))
    op.add_column("claims", sa.Column("fraud_explanation", sa.String(length=1024), nullable=True))
    op.add_column("claims", sa.Column("fraud_explanation_confidence", sa.Float(), nullable=True))
    op.add_column("claims", sa.Column("fraud_explanation_source", sa.String(length=64), nullable=True))
    op.add_column("claims", sa.Column("fraud_component_scores", sa.JSON(), nullable=True))
    op.add_column("claims", sa.Column("fraud_top_reasons", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "fraud_top_reasons")
    op.drop_column("claims", "fraud_component_scores")
    op.drop_column("claims", "fraud_explanation_source")
    op.drop_column("claims", "fraud_explanation_confidence")
    op.drop_column("claims", "fraud_explanation")
    op.drop_column("claims", "fraud_band")
    op.drop_column("claims", "fraud_score")