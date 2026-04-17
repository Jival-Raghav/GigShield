"""Trigger monitoring and disruption simulation routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_worker
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.worker import Worker
from schemas.disruption import DisruptionCreate, DisruptionResponse, TriggerCheck
from services import trigger_monitor
from services.claim_processing import evaluate_and_assign_claim

router = APIRouter(tags=["Triggers"])


@router.post("/triggers/check", response_model=list[DisruptionResponse], status_code=status.HTTP_200_OK)
async def check_triggers(
    payload: TriggerCheck,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> list[Disruption]:
    try:
        disruptions = await trigger_monitor.check_all_triggers(zone_id=payload.zone_id, db=db)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not disruptions:
        return []

    if isinstance(disruptions[0], Disruption):
        return disruptions

    records: list[Disruption] = []
    for item in disruptions:
        started_at = item.get("started_at") or datetime.now(timezone.utc)
        record = Disruption(
            zone_id=item["zone_id"],
            disruption_type=item["disruption_type"],
            severity=item["severity"],
            signal_source=item["signal_source"],
            is_confirmed=True,
            is_catastrophic=item.get("is_catastrophic", False),
            started_at=started_at,
            ended_at=item.get("ended_at"),
        )
        db.add(record)
        records.append(record)

    db.commit()
    for record in records:
        db.refresh(record)
    return records


@router.post("/triggers/simulate", status_code=status.HTTP_201_CREATED)
async def simulate_disruption(
    payload: DisruptionCreate,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> dict:
    started_at = payload.started_at or datetime.now(timezone.utc)

    disruption = Disruption(
        zone_id=payload.zone_id,
        disruption_type=payload.disruption_type,
        severity=payload.severity,
        signal_source=payload.signal_source,
        is_confirmed=True,
        is_catastrophic=payload.severity > 0.9,
        started_at=started_at,
        ended_at=payload.ended_at,
    )
    db.add(disruption)
    db.flush()

    initiated = 0
    if disruption.ended_at is not None:
        workers = db.query(Worker).filter(Worker.micro_zone_id == payload.zone_id).all()
        for worker in workers:
            policy = (
                db.query(Policy)
                .filter(Policy.worker_id == worker.id, Policy.is_active.is_(True))
                .order_by(Policy.created_at.desc())
                .first()
            )
            if policy is None:
                continue

            claim = Claim(
                worker_id=worker.id,
                policy_id=policy.id,
                disruption_id=disruption.id,
                status=ClaimStatusEnum.validating,
            )

            claim = evaluate_and_assign_claim(
                worker=worker,
                policy=policy,
                disruption=disruption,
                claim=claim,
                db=db,
            )

            db.add(claim)
            initiated += 1

    db.commit()
    db.refresh(disruption)

    return {
        "disruption": DisruptionResponse.model_validate(disruption).model_dump(),
        "claims_initiated": initiated,
    }


@router.get("/triggers/active/{zone_id}", response_model=list[DisruptionResponse], status_code=status.HTTP_200_OK)
def active_disruptions(
    zone_id: str,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> list[Disruption]:
    return (
        db.query(Disruption)
        .filter(Disruption.zone_id == zone_id, Disruption.ended_at.is_(None))
        .order_by(Disruption.started_at.desc())
        .all()
    )


@router.get("/triggers/claimable/{zone_id}", response_model=list[DisruptionResponse], status_code=status.HTTP_200_OK)
def claimable_disruptions(
    zone_id: str,
    lookback_days: int = 14,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> list[Disruption]:
    _ = current_worker
    safe_lookback = max(1, min(lookback_days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=safe_lookback)
    return (
        db.query(Disruption)
        .filter(
            Disruption.zone_id == zone_id,
            Disruption.ended_at.is_not(None),
            Disruption.ended_at >= since,
        )
        .order_by(Disruption.ended_at.desc())
        .all()
    )
