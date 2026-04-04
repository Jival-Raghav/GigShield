"""Policy ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CoverageTierEnum(str, enum.Enum):
    basic = "basic"
    standard = "standard"
    premium = "premium"


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    coverage_tier: Mapped[CoverageTierEnum] = mapped_column(
        Enum(CoverageTierEnum, name="coverage_tier_enum"), nullable=False
    )
    coverage_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    max_weekly_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    weekly_premium: Mapped[float] = mapped_column(Float, nullable=False)
    risk_multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    trust_discount: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    worker = relationship("Worker", back_populates="policies")
    claims = relationship("Claim", back_populates="policy")

    def __repr__(self) -> str:
        return (
            f"Policy(id={self.id}, worker_id={self.worker_id}, tier={self.coverage_tier.value}, "
            f"weekly_premium={self.weekly_premium}, active={self.is_active})"
        )
