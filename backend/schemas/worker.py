"""Pydantic schemas for workers."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.worker import PlatformEnum, VehicleTypeEnum


class WorkerCreate(BaseModel):
    name: str
    phone: str
    platform: PlatformEnum
    vehicle_type: VehicleTypeEnum
    micro_zone_id: str
    upi_id: str | None = None


class WorkerUpdate(BaseModel):
    avg_weekly_income: float | None = None
    micro_zone_id: str | None = None
    upi_id: str | None = None


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    upi_id: str | None
    platform: PlatformEnum
    vehicle_type: VehicleTypeEnum
    micro_zone_id: str
    tenure_weeks: int
    avg_weekly_income: float
    trust_score: float
    cold_start: bool
    created_at: datetime
    updated_at: datetime
