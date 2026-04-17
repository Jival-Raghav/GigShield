"""Claim lifecycle routes."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from dependencies import get_current_worker
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.payout import Payout, PaymentStatusEnum
from models.worker import Worker
from schemas.claim import ClaimCreate, ClaimResponse, ClaimStatusUpdate
from services import premium_engine
from services.claim_processing import evaluate_and_assign_claim, try_auto_pay_claim

router = APIRouter(tags=["Claims"])


def _sanitize_for_worker(claim: Claim) -> ClaimResponse:
    data = ClaimResponse.model_validate(claim).model_dump()
    data["audit_reason"] = None
    return ClaimResponse(**data)


@router.post("/claims/initiate", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def initiate_claim(
    payload: ClaimCreate,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> Claim:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot initiate claim for another worker")

    worker = db.query(Worker).filter(Worker.id == payload.worker_id).first()
    policy = db.query(Policy).filter(Policy.id == payload.policy_id).first()
    disruption = db.query(Disruption).filter(Disruption.id == payload.disruption_id).first()

    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if disruption is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disruption not found")
    if policy.worker_id != worker.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Policy does not belong to worker")
    if not policy.is_active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Active policy is required")
    if disruption.zone_id != worker.micro_zone_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Disruption is not in worker zone")
    if disruption.ended_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Manual claims are allowed only after the disruption has ended",
        )

    existing_claim = (
        db.query(Claim)
        .filter(Claim.worker_id == payload.worker_id, Claim.disruption_id == payload.disruption_id)
        .first()
    )
    if existing_claim is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claim already exists for this disruption",
        )

    claim = Claim(
        worker_id=payload.worker_id,
        policy_id=payload.policy_id,
        disruption_id=payload.disruption_id,
        status=ClaimStatusEnum.validating,
    )

    claim = evaluate_and_assign_claim(
        worker=worker,
        policy=policy,
        disruption=disruption,
        claim=claim,
        db=db,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        ip_address=payload.ip_address,
    )

    db.add(claim)
    db.flush()
    try_auto_pay_claim(claim=claim, policy=policy, db=db)
    db.commit()
    db.refresh(claim)
    return _sanitize_for_worker(claim)


@router.get("/claims/{claim_id}", response_model=ClaimResponse, status_code=status.HTTP_200_OK)
def get_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> Claim:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return _sanitize_for_worker(claim)


@router.get("/claims/worker/{worker_id}", response_model=list[ClaimResponse], status_code=status.HTTP_200_OK)
def list_worker_claims(
    worker_id: str,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> list[Claim]:
    rows = db.query(Claim).filter(Claim.worker_id == worker_id).order_by(Claim.created_at.desc()).all()
    return [_sanitize_for_worker(row) for row in rows]


@router.post("/claims/{claim_id}/status", response_model=ClaimResponse, status_code=status.HTTP_200_OK)
def update_claim_status(
    claim_id: str,
    payload: ClaimStatusUpdate,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> Claim:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    previous_status = claim.status
    claim.status = payload.status
    claim.audit_reason = payload.audit_reason

    finalized_statuses = {ClaimStatusEnum.approved, ClaimStatusEnum.rejected, ClaimStatusEnum.paid}
    if previous_status not in finalized_statuses and payload.status in finalized_statuses:
        worker = db.query(Worker).filter(Worker.id == claim.worker_id).first()
        if worker is not None:
            premium_engine.update_trust_score(worker=worker, baf_score=claim.baf_score or 0.6, db=db)

    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/claims/{claim_id}/payout/webhook", status_code=status.HTTP_200_OK)
async def payout_webhook(
    claim_id: str,
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    payload = await request.json()
    raw_body = await request.body()

    if not x_razorpay_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Razorpay signature")

    expected = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, x_razorpay_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Razorpay signature")

    event = payload.get("event")
    payout_entity = ((payload.get("payload") or {}).get("payout") or {}).get("entity") or {}
    razorpay_order_id = payout_entity.get("id")

    if razorpay_order_id:
        payout = db.query(Payout).filter(Payout.razorpay_order_id == razorpay_order_id).first()
        if payout is not None:
            if event == "payout.processed":
                payout.payment_status = PaymentStatusEnum.completed
                payout.completed_at = datetime.now(timezone.utc)
            elif event == "payout.failed":
                payout.payment_status = PaymentStatusEnum.failed

            db.add(payout)
            db.commit()

    return {"status": "ok"}
