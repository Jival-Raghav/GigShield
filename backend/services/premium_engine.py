"""Premium engine service functions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.claim import Claim
from models.worker import Worker
from services import baseline_engine, risk_model
from services.intelligence_signals import get_zone_intelligence_snapshot


_COVERAGE_TIERS = {
    "basic": {"coverage_ratio": 0.5, "max_weekly_coverage": 2000.0},
    "standard": {"coverage_ratio": 0.7, "max_weekly_coverage": 3500.0},
    "premium": {"coverage_ratio": 0.9, "max_weekly_coverage": 5000.0},
}

_ZONE_RISK_INDEX = {
    "high_risk": 1.08,
    "medium_risk": 1.02,
    "low_risk": 0.98,
}

_PLATFORM_VOLATILITY = {
    "swiggy": 1.02,
    "zomato": 1.02,
    "amazon": 1.0,
    "zepto": 1.04,
}

# Calibration knobs: aggressive reduction for affordable Indian market pricing
_DISRUPTION_LOSS_REALIZATION = 0.15
_RISK_AMPLIFICATION_WEIGHT = 0.05
_BASE_LOADING_FACTOR = 0.06


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
    intelligence = get_zone_intelligence_snapshot(worker.micro_zone_id)
    intelligence_pressure = float(intelligence.get("signal_pressure", 0.0))
    projected_weekly_income = max(baseline_income * (1.0 - (intelligence_pressure * 0.18)), 0.0)

    risk = risk_model.estimate_weekly_risk(zone_id=worker.micro_zone_id, db=db)
    expected_disruption_days = _clamp(float(risk.get("expected_disruption_days", 0.0)), 0.0, 7.0)
    expected_severity_per_day = _clamp(float(risk.get("expected_severity", 0.0)), 0.0, 1.0)
    disruption_week_fraction = _clamp(expected_disruption_days / 7.0, 0.0, 1.0)
    
    # Expected loss must use disruption-days as a fraction of the week, not a direct multiplier.
    expected_loss = min(
        projected_weekly_income
        * disruption_week_fraction
        * expected_severity_per_day
        * coverage_ratio
        * _DISRUPTION_LOSS_REALIZATION,
        max_weekly_coverage,
    )

    zone_bucket = _zone_risk_bucket(worker.micro_zone_id)
    zone_risk_index = _ZONE_RISK_INDEX[zone_bucket]
    platform_key = worker.platform.value.lower()
    platform_volatility_index = _PLATFORM_VOLATILITY.get(platform_key, 1.02)
    signal_loading = 1.0 + (intelligence_pressure * 0.08)
    risk_multiplier = min(zone_risk_index * platform_volatility_index * signal_loading, 1.5)
    # Expected loss already contains disruption-risk estimates, so use a damped risk adjustment here
    # to avoid counting the same risk signal twice.
    damped_risk_multiplier = 1.0 + ((risk_multiplier - 1.0) * _RISK_AMPLIFICATION_WEIGHT)

    # Trust adjustment: discount for high trust (>0.6), penalty for low trust (<0.6)
    # trust_score ranges from 0.1 to 1.0, neutral point is 0.6
    trust_adjustment = 1.0 + (0.6 - float(worker.trust_score)) * 0.25
    trust_adjustment = _clamp(trust_adjustment, 0.80, 1.20)

    loading_factor = _BASE_LOADING_FACTOR
    weekly_premium = expected_loss * (1.0 + loading_factor) * damped_risk_multiplier * trust_adjustment

    # Income-based affordability cap
    max_affordable_rates = {
        "basic": 0.025,
        "standard": 0.065,
        "premium": 0.115,
    }
    income_based_cap = projected_weekly_income * max_affordable_rates[tier_key]
    weekly_premium = min(weekly_premium, income_based_cap)

    return {
        "weekly_premium": round(max(weekly_premium, 0.0), 2),
        "expected_loss": round(max(expected_loss, 0.0), 2),
        "projected_weekly_income": round(projected_weekly_income, 2),
        "intelligence_pressure": round(intelligence_pressure, 3),
        "loading_factor": loading_factor,
        "risk_multiplier": round(risk_multiplier, 3),
        # Keep backward-compatible key used by API schema/routes/frontend.
        "trust_discount": round(trust_adjustment, 3),
        "trust_adjustment": round(trust_adjustment, 3),
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