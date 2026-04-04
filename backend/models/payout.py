"""Payout ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PaymentMethodEnum(str, enum.Enum):
    upi = "upi"
    bank_transfer = "bank_transfer"


class PaymentStatusEnum(str, enum.Enum):
    initiated = "initiated"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[PaymentMethodEnum] = mapped_column(
        Enum(PaymentMethodEnum, name="payment_method_enum"), nullable=False
    )
    payment_status: Mapped[PaymentStatusEnum] = mapped_column(
        Enum(PaymentStatusEnum, name="payment_status_enum"),
        default=PaymentStatusEnum.initiated,
        nullable=False,
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    claim = relationship("Claim", back_populates="payout")
    worker = relationship("Worker", back_populates="payouts")

    def __repr__(self) -> str:
        return (
            f"Payout(id={self.id}, claim_id={self.claim_id}, amount={self.amount}, "
            f"status={self.payment_status.value})"
        )
