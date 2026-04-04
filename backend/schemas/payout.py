"""Pydantic schemas for payouts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.payout import PaymentMethodEnum, PaymentStatusEnum


class PayoutCreate(BaseModel):
    claim_id: UUID
    worker_id: UUID
    amount: float
    payment_method: PaymentMethodEnum


class PayoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    worker_id: UUID
    amount: float
    payment_method: PaymentMethodEnum
    payment_status: PaymentStatusEnum
    razorpay_order_id: str | None
    initiated_at: datetime
    completed_at: datetime | None
