"""Pydantic schemas for worker income baseline calculations."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DailyIncomeCreate(BaseModel):
    worker_id: UUID
    date: date
    daily_income: float
    disruption_day: bool


class DailyIncomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    worker_id: UUID
    date: date
    daily_income: float
    disruption_day: bool
    clean_income: float | None
    created_at: datetime


class BaselineIncomeResponse(BaseModel):
    baseline_income: float
    confidence: float
    data_source: str
    weeks_of_data: int
