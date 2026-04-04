"""Pydantic schemas for policies and premium quotes."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.policy import CoverageTierEnum


class PolicyCreate(BaseModel):
    worker_id: UUID
    coverage_tier: CoverageTierEnum


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    worker_id: UUID
    coverage_tier: CoverageTierEnum
    coverage_ratio: float
    max_weekly_coverage: float
    weekly_premium: float
    risk_multiplier: float
    trust_discount: float
    is_active: bool
    valid_from: date
    valid_to: date
    created_at: datetime


class PremiumQuote(BaseModel):
    worker_id: UUID
    coverage_tier: CoverageTierEnum
    weekly_premium: float
    expected_loss: float
    loading_factor: float
    risk_multiplier: float
    trust_discount: float
    coverage_ratio: float
    max_weekly_coverage: float


class PremiumQuoteRequest(BaseModel):
    worker_id: UUID
    coverage_tier: CoverageTierEnum


class PremiumQuoteResponse(BaseModel):
    weekly_premium: float
    expected_loss: float
    loading_factor: float
    risk_multiplier: float
    trust_discount: float
    coverage_ratio: float
    max_weekly_coverage: float
