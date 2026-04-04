"""Shared claim evaluation logic used by routes and scheduler."""

from __future__ import annotations

from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.worker import Worker
from services import fraud_detection, payout_engine


def evaluate_and_assign_claim(
    *,
    worker: Worker,
    policy: Policy,
    disruption: Disruption,
    claim: Claim,
    db,
) -> Claim:
    """Populate claim metrics and status based on fraud and payout models."""
    claimed_zone_id = disruption.zone_id
    metadata = fraud_detection.build_claim_metadata(worker=worker, claimed_zone_id=claimed_zone_id)
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
    claim.signal_confidence = 1.0 - min(1.0, spoof_result.get("spoofing_signals_fired", 0) * 0.15)
    claim.behavior_confidence = baf_score
    claim.unified_confidence = (claim.signal_confidence + claim.behavior_confidence) / 2.0
    claim.spoofing_signals_fired = spoof_result.get("spoofing_signals_fired", 0)
    claim.syndicate_flag = spoof_result.get("syndicate_flag", False)

    spoof_audit = spoof_result.get("audit_required", False)
    low_baf_audit = baf_score < 0.4
    claim.audit_required = spoof_audit or low_baf_audit

    failed_signals = spoof_result.get("failed_signals", [])
    if claim.audit_required:
        reasons: list[str] = []
        if spoof_audit and failed_signals:
            reasons.append(f"Spoofing check flagged: {', '.join(failed_signals)}")
        if low_baf_audit:
            reasons.append(f"Low BAF score: {baf_score:.0%}")
        claim.audit_reason = "; ".join(reasons)
    else:
        claim.audit_reason = None

    if spoof_result.get("baf_modifier", 1.0) == 0.0:
        claim.status = ClaimStatusEnum.held
    elif claim.audit_required:
        claim.status = ClaimStatusEnum.pending
    elif baf_score >= 0.6:
        claim.status = ClaimStatusEnum.approved
    else:
        claim.status = ClaimStatusEnum.pending

    return claim
