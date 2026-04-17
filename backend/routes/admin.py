"""Admin analytics routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_admin_token
from scheduler import run_weekly_settlement_now
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.payout import Payout
from models.worker import Worker
from schemas.claim import ClaimScenarioInput
from services import admin_service, fraud_ai
from services.fraud_clusters import build_fraud_cluster_map
from services.claim_insights import build_claim_timeline, simulate_claim_scenario


class AdminClaimStatusUpdate(BaseModel):
    status: ClaimStatusEnum
    audit_reason: Optional[str] = None

router = APIRouter(tags=["Admin"])


@router.get("/admin/dashboard", status_code=status.HTTP_200_OK)
def admin_dashboard(
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
) -> dict:
    _ = current_admin
    return admin_service.get_dashboard_metrics(db)


@router.get("/admin/claims/flagged", status_code=status.HTTP_200_OK)
def flagged_claims(
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
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
            "unified_confidence": float(claim.unified_confidence or 0),
            "audit_required": claim.audit_required,
            "audit_reason": claim.audit_reason,
            **fraud_ai.admin_fraud_payload(claim),
            "status": claim.status.value,
            "created_at": claim.created_at.isoformat() if claim.created_at else None,
            "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
        }
        for claim, worker, disruption in rows
    ]


@router.get("/admin/zones/risk", status_code=status.HTTP_200_OK)
def zone_risk(
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
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


@router.get("/admin/fraud/clusters", status_code=status.HTTP_200_OK)
def fraud_clusters(
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
) -> dict:
    _ = current_admin
    return build_fraud_cluster_map(db)


@router.post("/admin/claims/{claim_id}/status", status_code=status.HTTP_200_OK)
def update_claim_status_admin(
    claim_id: str,
    payload: AdminClaimStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
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
    current_admin: Worker = Depends(get_current_admin_token),
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


def _manual_gateway_label(reference: str | None) -> str:
    value = (reference or "").upper()
    if "STRIPE_SANDBOX" in value:
        return "Stripe sandbox"
    if "RAZORPAY_TEST" in value:
        return "Razorpay test mode"
    if "UPI_SIMULATOR" in value:
        return "UPI simulator"
    return "manual gateway"


@router.get("/admin/payouts/log", status_code=status.HTTP_200_OK)
def payout_log(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
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
                    f"Settled by admin manual approval via {_manual_gateway_label(payout.razorpay_order_id)}" if mode == "manual_admin_settlement" else
                    "Settled via external provider flow"
                ),
                "audit_required": bool(claim.audit_required),
                "audit_reason": claim.audit_reason,
                "initiated_at": payout.initiated_at.isoformat() if payout.initiated_at else None,
                "completed_at": payout.completed_at.isoformat() if payout.completed_at else None,
            }
        )

    return result


@router.get("/admin/claims/{claim_id}/timeline", status_code=status.HTTP_200_OK)
def claim_timeline(
    claim_id: str,
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
) -> dict:
    _ = current_admin
    return build_claim_timeline(claim_id=claim_id, db=db)


@router.post("/admin/claims/{claim_id}/simulate", status_code=status.HTTP_200_OK)
def simulate_claim(
    claim_id: str,
    payload: ClaimScenarioInput,
    db: Session = Depends(get_db),
    current_admin: Worker = Depends(get_current_admin_token),
) -> dict:
    _ = current_admin
    return simulate_claim_scenario(claim_id=claim_id, overrides=payload.model_dump(exclude_none=True), db=db)
