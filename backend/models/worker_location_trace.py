"""Worker location trace ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class WorkerLocationTrace(Base):
    __tablename__ = "worker_location_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="browser_periodic")
    mapped_parent_zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mapped_fine_zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"WorkerLocationTrace(id={self.id}, worker_id={self.worker_id}, "
            f"zone={self.mapped_parent_zone_id}, fine_zone={self.mapped_fine_zone_id})"
        )
