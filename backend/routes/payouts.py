"""Payout routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_admin_token
from models.claim import Claim, ClaimStatusEnum
from models.payout import PaymentMethodEnum, PaymentStatusEnum, Payout
from models.worker import Worker
from schemas.payout import PayoutResponse
from services import payment_service

router = APIRouter(tags=["Payouts"])


@router.post("/payouts/{claim_id}/initiate", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
def initiate_payout(
    claim_id: str,
    gateway: Literal["upi_simulator", "razorpay_test", "stripe_sandbox"] = "upi_simulator",
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
) -> Payout:
    """Initiate payout for an approved claim. Admin only."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    if claim.status != ClaimStatusEnum.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot initiate payout for claim with status: {claim.status.value}. Claim must be approved.",
        )

    # Check if payout already exists
    existing_payout = db.query(Payout).filter(Payout.claim_id == claim_id).first()
    if existing_payout:
        if existing_payout.payment_status == PaymentStatusEnum.completed and claim.status != ClaimStatusEnum.paid:
            claim.status = ClaimStatusEnum.paid
            db.commit()
        return existing_payout

    # Create new payout and execute through selected gateway.
    payout = Payout(
        claim_id=claim.id,
        worker_id=claim.worker_id,
        amount=claim.payout_amount or 0.0,
        payment_method=PaymentMethodEnum.upi,
        payment_status=PaymentStatusEnum.initiated,
        razorpay_order_id=f"MANUAL-ADMIN-{gateway.upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
    )
    db.add(payout)
    db.commit()

    worker = db.query(Worker).filter(Worker.id == claim.worker_id).first()
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    payout = payment_service.initiate_gateway_payout(payout=payout, worker=worker, db=db, gateway=gateway)

    if payout.payment_status == PaymentStatusEnum.completed:
        claim.status = ClaimStatusEnum.paid
        db.commit()
    elif payout.payment_status in {PaymentStatusEnum.processing, PaymentStatusEnum.initiated}:
        claim.status = ClaimStatusEnum.approved
        db.commit()

    return payout
