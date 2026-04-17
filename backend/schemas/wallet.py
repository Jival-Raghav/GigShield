"""Pydantic schemas for mock worker wallet responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WalletTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: float
    entry_type: str
    description: str
    payout_id: str | None
    claim_id: str | None
    created_at: datetime


class WorkerWalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    worker_id: str
    balance: float
    updated_at: datetime
    recent_transactions: list[WalletTransactionResponse]
