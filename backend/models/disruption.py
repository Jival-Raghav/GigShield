"""Disruption ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class DisruptionTypeEnum(str, enum.Enum):
    rainfall = "rainfall"
    aqi = "aqi"
    flood = "flood"
    curfew = "curfew"
    platform_outage = "platform_outage"
    extreme_temperature = "extreme_temperature"


class Disruption(Base):
    __tablename__ = "disruptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    disruption_type: Mapped[DisruptionTypeEnum] = mapped_column(
        Enum(DisruptionTypeEnum, name="disruption_type_enum"), nullable=False
    )
    severity: Mapped[float] = mapped_column(Float, nullable=False)
    signal_source: Mapped[str] = mapped_column(String(64), nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_catastrophic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    claims = relationship("Claim", back_populates="disruption")

    def __repr__(self) -> str:
        return (
            f"Disruption(id={self.id}, zone_id={self.zone_id}, type={self.disruption_type.value}, "
            f"severity={self.severity}, confirmed={self.is_confirmed})"
        )
