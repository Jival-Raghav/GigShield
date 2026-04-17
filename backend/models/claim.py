"""Claim ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ClaimStatusEnum(str, enum.Enum):
    pending = "pending"
    validating = "validating"
    approved = "approved"
    held = "held"
    rejected = "rejected"
    paid = "paid"


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    disruption_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disruptions.id"), nullable=False
    )
    status: Mapped[ClaimStatusEnum] = mapped_column(
        Enum(ClaimStatusEnum, name="claim_status_enum"), default=ClaimStatusEnum.pending, nullable=False
    )
    baf_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    payout_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    income_lost: Mapped[float | None] = mapped_column(Float, nullable=True)
    eligible_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity_smoothed: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    behavior_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    unified_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    fraud_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fraud_band: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fraud_explanation: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    fraud_explanation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    fraud_explanation_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fraud_component_scores: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    fraud_top_reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    spoofing_signals_fired: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    syndicate_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    audit_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    audit_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    worker = relationship("Worker", back_populates="claims")
    policy = relationship("Policy", back_populates="claims")
    disruption = relationship("Disruption", back_populates="claims")
    payout = relationship("Payout", back_populates="claim", uselist=False)

    def __repr__(self) -> str:
        return (
            f"Claim(id={self.id}, worker_id={self.worker_id}, status={self.status.value}, "
            f"payout_amount={self.payout_amount}, audit_required={self.audit_required})"
        )
