"""Registration service helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.worker import Worker
from schemas.worker import WorkerCreate


def _normalize_phone(phone: str) -> str:
    compact = re.sub(r"[\s\-()]", "", phone.strip())
    if compact.startswith("+"):
        normalized = "+" + re.sub(r"\D", "", compact[1:])
    else:
        normalized = re.sub(r"\D", "", compact)

    if not normalized.startswith("+"):
        normalized = "+" + normalized

    digits_count = len(normalized) - 1
    if digits_count < 10 or digits_count > 15:
        raise ValueError("Phone number must contain 10 to 15 digits")

    return normalized


def register_worker(payload: WorkerCreate, db: Session) -> Worker:
    """Register and stage a worker record for commit by the route layer."""
    normalized_phone = _normalize_phone(payload.phone)

    existing = db.query(Worker).filter(Worker.phone == normalized_phone).first()
    if existing is not None:
        raise ValueError("Phone number already exists")

    now = datetime.now(timezone.utc)
    worker = Worker(
        name=payload.name.strip(),
        phone=normalized_phone,
        upi_id=(payload.upi_id.strip() if payload.upi_id else None),
        platform=payload.platform,
        vehicle_type=payload.vehicle_type,
        micro_zone_id=payload.micro_zone_id.strip(),
        tenure_weeks=0,
        avg_weekly_income=0.0,
        trust_score=0.6,
        cold_start=True,
        created_at=now,
        updated_at=now,
    )
    db.add(worker)
    db.flush()
    return worker
