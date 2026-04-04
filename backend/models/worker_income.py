"""Worker income and peer cluster ORM models."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.worker import PlatformEnum, VehicleTypeEnum


class WorkerDailyIncome(Base):
    __tablename__ = "worker_daily_income"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    daily_income: Mapped[float] = mapped_column(Float, nullable=False)
    disruption_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clean_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"WorkerDailyIncome(id={self.id}, worker_id={self.worker_id}, date={self.date}, "
            f"daily_income={self.daily_income}, disruption_day={self.disruption_day})"
        )


class PeerClusterStats(Base):
    __tablename__ = "peer_cluster_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    micro_zone_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum, name="platform_enum"), nullable=False)
    vehicle_type: Mapped[VehicleTypeEnum] = mapped_column(
        Enum(VehicleTypeEnum, name="vehicle_type_enum"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    peer_avg_income: Mapped[float] = mapped_column(Float, nullable=False)
    peer_income_variance: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"PeerClusterStats(id={self.id}, zone={self.micro_zone_id}, platform={self.platform.value}, "
            f"vehicle_type={self.vehicle_type.value}, week_start={self.week_start})"
        )
