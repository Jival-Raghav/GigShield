"""Shared claim evaluation logic used by routes and scheduler."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.payout import PaymentMethodEnum, PaymentStatusEnum, Payout
from models.policy import Policy
from models.worker import Worker
from services import fraud_ai, fraud_detection, payout_engine


def evaluate_and_assign_claim(
    *,
    worker: Worker,
    policy: Policy,
    disruption: Disruption,
    claim: Claim,
    db,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_meters: float | None = None,
    ip_address: str | None = None,
) -> Claim:
    """Populate claim metrics and status based on fraud and payout models."""
    claimed_zone_id = disruption.zone_id
    metadata = fraud_detection.build_claim_metadata(
        worker=worker,
        claimed_zone_id=claimed_zone_id,
        db=db,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
        ip_address=ip_address,
        claim_timestamp=claim.created_at,
    )
    spoof_result = fraud_detection.run_spoofing_check(
        worker=worker,
        claimed_zone_id=claimed_zone_id,
        claim_metadata=metadata,
        db=db,
    )

    baf_score = payout_engine.compute_baf(worker=worker, claim=claim, disruption=disruption, db=db)
    payout_result = payout_engine.calculate_payout(
        worker=worker,
        claim=claim,
        policy=policy,
        disruption=disruption,
        baf_score=baf_score,
    )

    claim.baf_score = baf_score
    claim.payout_amount = payout_result.get("adjusted_payout")
    claim.income_lost = payout_result.get("income_lost")
    claim.eligible_hours = payout_result.get("eligible_hours")
    claim.severity_smoothed = payout_result.get("severity_smoothed")

    fraud_assessment = fraud_ai.assess_claim_fraud(
        db=db,
        worker=worker,
        disruption=disruption,
        claim_metadata=metadata,
        spoof_result=spoof_result,
        baf_score=baf_score,
    )

    claim.signal_confidence = round(float(max(0.0, 1.0 - (fraud_assessment.fraud_score / 100.0))), 4)
    claim.behavior_confidence = round(float(baf_score), 4)
    claim.unified_confidence = round(float((claim.signal_confidence + claim.behavior_confidence) / 2.0), 4)
    claim.fraud_score = round(float(fraud_assessment.fraud_score), 2)
    claim.fraud_band = fraud_assessment.fraud_band
    claim.fraud_explanation = fraud_assessment.explanation
    claim.fraud_explanation_confidence = round(float(fraud_assessment.explanation_confidence), 3)
    claim.fraud_explanation_source = fraud_assessment.explanation_source
    claim.fraud_component_scores = fraud_assessment.component_scores
    claim.fraud_top_reasons = fraud_assessment.top_reasons
    claim.spoofing_signals_fired = spoof_result.get("spoofing_signals_fired", 0)
    claim.syndicate_flag = spoof_result.get("syndicate_flag", False)

    spoof_audit = spoof_result.get("audit_required", False)
    low_baf_audit = baf_score < 0.4
    fraud_score_audit = fraud_assessment.fraud_score >= 55.0
    claim.audit_required = spoof_audit or low_baf_audit or fraud_score_audit

    failed_signals = spoof_result.get("failed_signals", [])
    if claim.audit_required:
        reasons: list[str] = []
        reasons.append(f"Fraud score {fraud_assessment.fraud_score:.0f}/100 ({fraud_assessment.fraud_band})")
        if spoof_audit and failed_signals:
            reasons.append(f"Spoofing check flagged: {', '.join(failed_signals)}")
        if low_baf_audit:
            reasons.append(f"Low BAF score: {baf_score:.0%}")
        if fraud_assessment.top_reasons:
            reasons.append(f"Top factors: {', '.join(fraud_assessment.top_reasons[:3])}")
        reasons.append(f"Reasoning: {fraud_assessment.explanation}")
        claim.audit_reason = "; ".join(reasons)[:255]
    else:
        claim.audit_reason = None

    if spoof_result.get("baf_modifier", 1.0) == 0.0 or fraud_assessment.fraud_score >= 75.0:
        claim.status = ClaimStatusEnum.held
    elif claim.audit_required:
        claim.status = ClaimStatusEnum.pending
    elif baf_score >= 0.6:
        claim.status = ClaimStatusEnum.approved
    else:
        claim.status = ClaimStatusEnum.pending

    return claim


def try_auto_pay_claim(*, claim: Claim, policy: Policy, db, reference_prefix: str = "AUTO-INSTANT") -> bool:
    """Auto-pay low-risk approved claims immediately, respecting weekly coverage cap."""
    if claim.status != ClaimStatusEnum.approved:
        return False
    if claim.audit_required:
        return False
    if float(claim.fraud_score or 100.0) >= 55.0:
        return False

    payable_amount = round(float(claim.payout_amount or 0.0), 2)
    if payable_amount <= 0.0:
        return False

    now = datetime.now(timezone.utc)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    paid_this_week = (
        db.query(func.coalesce(func.sum(Payout.amount), 0.0))
        .filter(
            Payout.worker_id == claim.worker_id,
            Payout.initiated_at >= week_start,
            Payout.initiated_at < week_end,
            Payout.payment_status == PaymentStatusEnum.completed,
        )
        .scalar()
    )
    paid_total = float(paid_this_week or 0.0)
    remaining_coverage = max(float(policy.max_weekly_coverage) - paid_total, 0.0)
    payout_amount = round(min(payable_amount, remaining_coverage), 2)
    if payout_amount <= 0.0:
        return False

    claim.payout_amount = payout_amount
    claim.status = ClaimStatusEnum.paid

    payout = Payout(
        claim_id=claim.id,
        worker_id=claim.worker_id,
        amount=payout_amount,
        payment_method=PaymentMethodEnum.upi,
        payment_status=PaymentStatusEnum.completed,
        razorpay_order_id=(
            f"{reference_prefix}-{week_start.strftime('%Y%m%d')}-{str(claim.id).replace('-', '')[:10]}"
        ),
        completed_at=now,
    )
    db.add(payout)
    return True
