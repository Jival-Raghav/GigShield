"""Pydantic schemas for claims."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.claim import ClaimStatusEnum


class ClaimCreate(BaseModel):
    worker_id: UUID
    policy_id: UUID
    disruption_id: UUID


class ClaimStatusUpdate(BaseModel):
    status: ClaimStatusEnum
    audit_reason: str | None = None


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    worker_id: UUID
    policy_id: UUID
    disruption_id: UUID
    status: ClaimStatusEnum
    baf_score: float | None
    payout_amount: float | None
    income_lost: float | None
    eligible_hours: float | None
    severity_smoothed: float | None
    signal_confidence: float | None
    behavior_confidence: float | None
    unified_confidence: float | None
    spoofing_signals_fired: int
    syndicate_flag: bool
    audit_required: bool
    audit_reason: str | None
    created_at: datetime
    updated_at: datetime
