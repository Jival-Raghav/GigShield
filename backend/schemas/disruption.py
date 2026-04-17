"""Pydantic schemas for disruptions and trigger checks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from models.disruption import DisruptionTypeEnum


class DisruptionCreate(BaseModel):
    zone_id: str
    disruption_type: DisruptionTypeEnum
    severity: float
    signal_source: str
    started_at: datetime | None = None
    ended_at: datetime | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> "DisruptionCreate":
        if self.started_at and self.ended_at and self.ended_at <= self.started_at:
            raise ValueError("ended_at must be later than started_at")
        return self


class TriggerCheck(BaseModel):
    zone_id: str


class TriggerCheckResponse(BaseModel):
    active_disruptions: list["DisruptionResponse"]


class DisruptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    zone_id: str
    disruption_type: DisruptionTypeEnum
    severity: float
    signal_source: str
    is_confirmed: bool
    is_catastrophic: bool
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
