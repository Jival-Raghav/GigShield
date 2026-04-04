"""Worker ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PlatformEnum(str, enum.Enum):
    swiggy = "swiggy"
    zomato = "zomato"
    amazon = "amazon"
    zepto = "zepto"


class VehicleTypeEnum(str, enum.Enum):
    bike = "bike"
    cycle = "cycle"
    other = "other"


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    upi_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum, name="platform_enum"), nullable=False)
    vehicle_type: Mapped[VehicleTypeEnum] = mapped_column(
        Enum(VehicleTypeEnum, name="vehicle_type_enum"), nullable=False
    )
    micro_zone_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenure_weeks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_weekly_income: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    cold_start: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    policies = relationship("Policy", back_populates="worker", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="worker", cascade="all, delete-orphan")
    payouts = relationship("Payout", back_populates="worker", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"Worker(id={self.id}, phone={self.phone}, platform={self.platform.value}, "
            f"zone={self.micro_zone_id}, trust_score={self.trust_score})"
        )
