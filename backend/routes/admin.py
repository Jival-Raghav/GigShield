"""Admin analytics routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_admin
from scheduler import run_weekly_settlement_now
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.payout import Payout
from models.worker import Worker


class AdminClaimStatusUpdate(BaseModel):
    status: ClaimStatusEnum
    audit_reason: Optional[str] = None

router = APIRouter(tags=["Admin"])


@router.get("/admin/dashboard", status_code=status.HTTP_200_OK)
def admin_dashboard(
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin),
) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    total_active_policies = db.query(func.count(Policy.id)).filter(Policy.is_active.is_(True)).scalar() or 0
    total_claims_today = db.query(func.count(Claim.id)).filter(Claim.created_at >= today_start).scalar() or 0
    total_payouts_today = (
        db.query(func.coalesce(func.sum(Payout.amount), 0.0))
        .filter(Payout.completed_at.is_not(None), Payout.completed_at >= today_start)
        .scalar()
        or 0.0
    )
    claims_pending_audit = (
        db.query(func.count(Claim.id))
        .filter(Claim.audit_required.is_(True), Claim.status != "paid")
        .scalar()
        or 0
    )
    active_disruptions = db.query(func.count(Disruption.id)).filter(Disruption.ended_at.is_(None)).scalar() or 0
    avg_baf_score = (
        db.query(func.coalesce(func.avg(Claim.baf_score), 0.0)).filter(Claim.created_at >= today_start).scalar() or 0.0
    )
    total_premiums_collected_this_week = (
        db.query(func.coalesce(func.sum(Policy.weekly_premium), 0.0)).filter(Policy.created_at >= week_start).scalar() or 0.0
    )
    loss_ratio = (
        float(total_payouts_today) / float(total_premiums_collected_this_week)
        if float(total_premiums_collected_this_week) > 0
        else 0.0
    )

    return {
        "total_active_policies": int(total_active_policies),
        "total_claims_today": int(total_claims_today),
        "total_payouts_today": float(total_payouts_today),
        "claims_pending_audit": int(claims_pending_audit),
        "active_disruptions": int(active_disruptions),
        "avg_baf_score": float(avg_baf_score),
        "loss_ratio": float(loss_ratio),
    }


@router.get("/admin/claims/flagged", status_code=status.HTTP_200_OK)
def flagged_claims(
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin),
) -> list[dict]:
    rows = (
        db.query(Claim, Worker, Disruption)
        .join(Worker, Worker.id == Claim.worker_id)
        .join(Disruption, Disruption.id == Claim.disruption_id)
        .filter(Claim.audit_required.is_(True))
        .order_by(Claim.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(claim.id),
            "worker_id": str(claim.worker_id),
            "policy_id": str(claim.policy_id),
            "disruption_id": str(claim.disruption_id),
            "worker_name": worker.name,
            "zone_id": worker.micro_zone_id,
            "disruption_type": disruption.disruption_type.value,
            "payout_amount": float(claim.payout_amount or 0),
            "baf_score": float(claim.baf_score or 0),
            "signal_confidence": float(claim.signal_confidence or 0),
            "behavior_confidence": float(claim.behavior_confidence or 0),
            "audit_required": claim.audit_required,
            "audit_reason": claim.audit_reason,
            "status": claim.status.value,
            "created_at": claim.created_at.isoformat() if claim.created_at else None,
            "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
        }
        for claim, worker, disruption in rows
    ]


@router.get("/admin/zones/risk", status_code=status.HTTP_200_OK)
def zone_risk(
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin),
) -> list[dict]:
    start_time = datetime.now(timezone.utc) - timedelta(days=7)
    disruption_stats = (
        db.query(
            Disruption.zone_id,
            func.count(Disruption.id).label("disruption_count"),
            func.avg(Disruption.severity).label("avg_severity"),
        )
        .filter(Disruption.created_at >= start_time)
        .group_by(Disruption.zone_id)
        .order_by(func.count(Disruption.id).desc())
        .all()
    )

    result: list[dict] = []
    for zone_id, count, avg_severity in disruption_stats:
        result.append(
            {
                "zone_id": zone_id,
                "disruption_count": int(count),
                "avg_severity": float(avg_severity or 0.0),
            }
        )
    return result


@router.post("/admin/claims/{claim_id}/status", status_code=status.HTTP_200_OK)
def update_claim_status_admin(
    claim_id: str,
    payload: AdminClaimStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin),
) -> dict:
    """Admin endpoint to approve/reject claims."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    previous_status = claim.status
    claim.status = payload.status
    if payload.audit_reason:
        claim.audit_reason = payload.audit_reason

    db.commit()
    db.refresh(claim)

    return {
        "id": str(claim.id),
        "status": claim.status.value,
        "audit_reason": claim.audit_reason,
        "payout_amount": float(claim.payout_amount or 0),
        "message": f"Claim status updated from {previous_status.value} to {claim.status.value}",
    }


@router.post("/admin/settlements/run", status_code=status.HTTP_200_OK)
def run_settlement_manually(
    mode: str = "previous_week",
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin),
) -> dict:
    """Manually trigger weekly settlement for demo/testing."""
    safe_mode = mode.strip().lower()
    if safe_mode not in {"previous_week", "current_week"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="mode must be previous_week or current_week")
    _ = db
    return run_weekly_settlement_now(mode=safe_mode)


def _payout_mode(razorpay_order_id: str | None) -> str:
    if not razorpay_order_id:
        return "legacy"
    if razorpay_order_id.startswith("AUTO-WEEKLY-"):
        return "auto_weekly_settlement"
    if razorpay_order_id.startswith("MANUAL-ADMIN-"):
        return "manual_admin_settlement"
    return "provider_webhook"


@router.get("/admin/payouts/log", status_code=status.HTTP_200_OK)
def payout_log(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin),
) -> list[dict]:
    """Recent payout log for admin audit and payout tracking notes."""
    safe_limit = max(1, min(limit, 500))

    rows = (
        db.query(Payout, Claim, Worker, Policy)
        .join(Claim, Claim.id == Payout.claim_id)
        .join(Worker, Worker.id == Payout.worker_id)
        .join(Policy, Policy.id == Claim.policy_id)
        .order_by(Payout.initiated_at.desc())
        .limit(safe_limit)
        .all()
    )

    result: list[dict] = []
    for payout, claim, worker, policy in rows:
        mode = _payout_mode(payout.razorpay_order_id)
        result.append(
            {
                "payout_id": str(payout.id),
                "claim_id": str(claim.id),
                "worker_id": str(worker.id),
                "worker_name": worker.name,
                "worker_phone": worker.phone,
                "zone_id": worker.micro_zone_id,
                "policy_id": str(policy.id),
                "coverage_tier": policy.coverage_tier.value,
                "amount": float(payout.amount),
                "payment_status": payout.payment_status.value,
                "payment_method": payout.payment_method.value,
                "settlement_mode": mode,
                "settlement_note": (
                    "Settled by weekly auto settlement" if mode == "auto_weekly_settlement" else
                    "Settled by admin manual approval" if mode == "manual_admin_settlement" else
                    "Settled via external provider flow"
                ),
                "audit_required": bool(claim.audit_required),
                "audit_reason": claim.audit_reason,
                "initiated_at": payout.initiated_at.isoformat() if payout.initiated_at else None,
                "completed_at": payout.completed_at.isoformat() if payout.completed_at else None,
            }
        )

    return result
