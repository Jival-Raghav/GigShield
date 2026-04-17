"""Add worker wallet tables for mock payout balance.

Revision ID: 20260417_02
Revises: 20260417_01
Create Date: 2026-04-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260417_02"
down_revision = "20260417_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    wallet_entry_type_enum = sa.Enum("credit", "debit", name="wallet_entry_type_enum")
    wallet_entry_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "worker_wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_id"),
    )
    op.create_index("ix_worker_wallets_worker_id", "worker_wallets", ["worker_id"], unique=False)

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payout_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entry_type", wallet_entry_type_enum, nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["worker_wallets.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.ForeignKeyConstraint(["payout_id"], ["payouts.id"]),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payout_id"),
    )
    op.create_index("ix_wallet_transactions_worker_id", "wallet_transactions", ["worker_id"], unique=False)
    op.create_index("ix_wallet_transactions_created_at", "wallet_transactions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wallet_transactions_created_at", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_worker_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")

    op.drop_index("ix_worker_wallets_worker_id", table_name="worker_wallets")
    op.drop_table("worker_wallets")

    wallet_entry_type_enum = sa.Enum("credit", "debit", name="wallet_entry_type_enum")
    wallet_entry_type_enum.drop(op.get_bind(), checkfirst=True)
