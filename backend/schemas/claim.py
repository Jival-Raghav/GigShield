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
    latitude: float | None = None
    longitude: float | None = None
    accuracy_meters: float | None = None
    ip_address: str | None = None


class ClaimStatusUpdate(BaseModel):
    status: ClaimStatusEnum
    audit_reason: str | None = None


class ClaimScenarioInput(BaseModel):
    rainfall_mm: float | None = None
    aqi: float | None = None
    curfew_level: str | None = None
    worker_movement: str | None = None
    gps_zone: str | None = None
    ip_zone: str | None = None
    wind_speed_kph: float | None = None
    disruption_severity: float | None = None
    external_pressure: float | None = None


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
    fraud_score: float | None
    fraud_band: str | None
    fraud_explanation: str | None
    fraud_explanation_confidence: float | None
    fraud_explanation_source: str | None
    fraud_component_scores: dict[str, float] | None
    fraud_top_reasons: list[str] | None
    created_at: datetime
    updated_at: datetime
