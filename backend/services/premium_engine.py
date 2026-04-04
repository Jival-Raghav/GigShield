"""Premium engine service functions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.claim import Claim
from models.worker import Worker
from services import baseline_engine, risk_model


_COVERAGE_TIERS = {
    "basic": {"coverage_ratio": 0.5, "max_weekly_coverage": 2000.0},
    "standard": {"coverage_ratio": 0.7, "max_weekly_coverage": 3500.0},
    "premium": {"coverage_ratio": 0.9, "max_weekly_coverage": 5000.0},
}

_ZONE_RISK_INDEX = {
    "high_risk": 1.4,
    "medium_risk": 1.1,
    "low_risk": 0.9,
}

_PLATFORM_VOLATILITY = {
    "swiggy": 1.1,
    "zomato": 1.1,
    "amazon": 1.0,
    "zepto": 1.2,
}


def _zone_risk_bucket(micro_zone_id: str) -> str:
    zone = micro_zone_id.lower()
    if any(token in zone for token in ["high", "flood", "coastal", "river", "dense", "central"]):
        return "high_risk"
    if any(token in zone for token in ["low", "suburb", "outskirts", "rural"]):
        return "low_risk"
    return "medium_risk"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def calculate_premium(worker: Worker, coverage_tier: str, db: Session) -> dict:
    """Calculate weekly premium using baseline, risk, and trust factors."""
    tier_key = coverage_tier.lower().strip()
    if tier_key not in _COVERAGE_TIERS:
        raise ValueError(f"Unsupported coverage tier: {coverage_tier}")

    tier = _COVERAGE_TIERS[tier_key]
    coverage_ratio = float(tier["coverage_ratio"])
    max_weekly_coverage = float(tier["max_weekly_coverage"])

    baseline_result = baseline_engine.compute_baseline_income(worker=worker, db=db)
    baseline_income = float(baseline_result.get("baseline_income", 0.0))

    risk = risk_model.estimate_weekly_risk(zone_id=worker.micro_zone_id, db=db)
    expected_disruption_days = max(float(risk["expected_disruption_days"]), 1.2)
    expected_severity_per_day = max(float(risk["expected_severity"]), 0.40)
    
    # Expected loss is proportional to coverage ratio (higher coverage = more potential payout)
    expected_loss = min(
        baseline_income * expected_disruption_days * expected_severity_per_day * coverage_ratio,
        max_weekly_coverage,
    )

    zone_bucket = _zone_risk_bucket(worker.micro_zone_id)
    zone_risk_index = _ZONE_RISK_INDEX[zone_bucket]
    platform_key = worker.platform.value.lower()
    platform_volatility_index = _PLATFORM_VOLATILITY.get(platform_key, 1.1)
    risk_multiplier = min(zone_risk_index * platform_volatility_index, 2.0)

    trust_discount = 1.0 - (float(worker.trust_score) - 0.6) * 0.1
    trust_discount = _clamp(trust_discount, 0.94, 1.06)

    loading_factor = 0.35
    # Premium is based on expected_loss directly (higher coverage = higher premium)
    weekly_premium = expected_loss * (1.0 + loading_factor) * risk_multiplier * trust_discount

    return {
        "weekly_premium": round(max(weekly_premium, 0.0), 2),
        "expected_loss": round(max(expected_loss, 0.0), 2),
        "loading_factor": loading_factor,
        "risk_multiplier": round(risk_multiplier, 3),
        "trust_discount": round(trust_discount, 3),
        "coverage_ratio": coverage_ratio,
        "max_weekly_coverage": max_weekly_coverage,
    }


def update_trust_score(worker: Worker, baf_score: float, db: Session) -> float:
    """Update worker trust score after claim settlement behavior."""
    if worker.cold_start:
        claim_count = db.query(Claim).filter(Claim.worker_id == worker.id).count()
        worker.trust_score = 0.6
        if claim_count >= 4:
            worker.cold_start = False

        db.add(worker)
        db.commit()
        db.refresh(worker)
        return float(worker.trust_score)

    score = _clamp(float(baf_score), 0.0, 1.0)
    weight = 0.35 if score < 0.4 else 0.20
    new_trust = (1.0 - weight) * float(worker.trust_score) + weight * score
    worker.trust_score = _clamp(new_trust, 0.1, 1.0)

    db.add(worker)
    db.commit()
    db.refresh(worker)
    return float(worker.trust_score)
