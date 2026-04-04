"""Payout routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_admin
from models.claim import Claim, ClaimStatusEnum
from models.payout import PaymentMethodEnum, PaymentStatusEnum, Payout
from models.worker import Worker
from schemas.payout import PayoutResponse

router = APIRouter(tags=["Payouts"])


@router.post("/payouts/{claim_id}/initiate", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
def initiate_payout(
    claim_id: str,
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin),
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
        # Mark claim as paid if not already
        if claim.status != ClaimStatusEnum.paid:
            claim.status = ClaimStatusEnum.paid
            db.commit()
        return existing_payout

    # Create new payout and mark as completed (simulating instant UPI transfer)
    payout = Payout(
        claim_id=claim.id,
        worker_id=claim.worker_id,
        amount=claim.payout_amount or 0.0,
        payment_method=PaymentMethodEnum.upi,
        payment_status=PaymentStatusEnum.completed,
        razorpay_order_id=f"MANUAL-ADMIN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(payout)
    
    # Update claim status to paid
    claim.status = ClaimStatusEnum.paid
    
    db.commit()
    db.refresh(payout)

    return payout
