"""Admin analytics service functions."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.payout import Payout


def get_dashboard_metrics(db: Session) -> dict:
    """Aggregate insurer dashboard KPIs for current day and week."""
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
        .filter(Claim.audit_required.is_(True), Claim.status != ClaimStatusEnum.paid)
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

    payout_today = float(total_payouts_today)
    premium_week = float(total_premiums_collected_this_week)
    loss_ratio = payout_today / premium_week if premium_week > 0 else 0.0

    return {
        "total_active_policies": int(total_active_policies),
        "total_claims_today": int(total_claims_today),
        "total_payouts_today": payout_today,
        "claims_pending_audit": int(claims_pending_audit),
        "active_disruptions": int(active_disruptions),
        "avg_baf_score": float(avg_baf_score),
        "loss_ratio": float(loss_ratio),
    }


def get_zone_risk_summary(db: Session) -> list[dict]:
    """Return disruption and claim impact metrics grouped by zone for last 7 days."""
    start_time = datetime.now(timezone.utc) - timedelta(days=7)
    disruptions = db.query(Disruption).filter(Disruption.created_at >= start_time).all()
    if not disruptions:
        return []

    disruption_ids = [d.id for d in disruptions]
    claims_by_disruption: dict = {}
    payouts_by_disruption: dict = {}

    claim_rows = (
        db.query(Claim.disruption_id, func.count(Claim.id), func.coalesce(func.sum(Claim.payout_amount), 0.0))
        .filter(Claim.disruption_id.in_(disruption_ids))
        .group_by(Claim.disruption_id)
        .all()
    )
    for disruption_id, claim_count, payout_sum in claim_rows:
        claims_by_disruption[disruption_id] = int(claim_count or 0)
        payouts_by_disruption[disruption_id] = float(payout_sum or 0.0)

    zone_map: dict[str, dict] = {}
    for disruption in disruptions:
        bucket = zone_map.setdefault(
            disruption.zone_id,
            {
                "zone_id": disruption.zone_id,
                "disruption_count": 0,
                "severity_sum": 0.0,
                "types": Counter(),
                "total_claims_triggered": 0,
                "total_payout_amount": 0.0,
            },
        )
        bucket["disruption_count"] += 1
        bucket["severity_sum"] += float(disruption.severity)
        bucket["types"][disruption.disruption_type.value] += 1
        bucket["total_claims_triggered"] += claims_by_disruption.get(disruption.id, 0)
        bucket["total_payout_amount"] += payouts_by_disruption.get(disruption.id, 0.0)

    summary: list[dict] = []
    for bucket in zone_map.values():
        common_type = "unknown"
        if bucket["types"]:
            common_type = bucket["types"].most_common(1)[0][0]

        summary.append(
            {
                "zone_id": bucket["zone_id"],
                "disruption_count": int(bucket["disruption_count"]),
                "avg_severity": float(bucket["severity_sum"] / max(bucket["disruption_count"], 1)),
                "most_common_type": common_type,
                "total_claims_triggered": int(bucket["total_claims_triggered"]),
                "total_payout_amount": float(round(bucket["total_payout_amount"], 2)),
            }
        )

    summary.sort(key=lambda row: row["disruption_count"], reverse=True)
    return summary
