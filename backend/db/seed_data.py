"""
GigShield Seed Data Generator
==============================
Populates the database with 12 weeks of realistic
gig worker income data for 3 test workers.

Run with:
    python -m backend.db.seed_data

Requirements:
    - Database must be running (docker-compose up)
    - Tables must exist (alembic upgrade head OR app startup)
"""

import random
import uuid
from datetime import date, datetime, timedelta, timezone

import numpy as np
from sqlalchemy.orm import Session

from database import SessionLocal
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption, DisruptionTypeEnum
from models.policy import CoverageTierEnum, Policy
from models.payout import PaymentMethodEnum, PaymentStatusEnum, Payout
from models.worker import Worker
from models.worker_income import PeerClusterStats, WorkerDailyIncome
from models.worker_location_trace import WorkerLocationTrace
from services.zone_granularity import map_coordinates_to_zone, parent_zone_for, zone_coordinates_for

# ─────────────────────────────────────────────
# FIXED SEED — every teammate gets identical data
# ─────────────────────────────────────────────
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ─────────────────────────────────────────────
# TIME WINDOW
# 84 days = 12 weeks ending yesterday
# ─────────────────────────────────────────────
END_DATE   = date.today() - timedelta(days=1)
START_DATE = END_DATE - timedelta(days=83)
ALL_DATES  = [START_DATE + timedelta(days=i) for i in range(84)]

def utcnow():
    return datetime.now(timezone.utc)

# ─────────────────────────────────────────────
# ZONE / WORKER PROFILES
# Covers all seeded parent and fine zones used across the pipeline.
# ─────────────────────────────────────────────
WORKER_PROFILES = [
    {
        "id": str(uuid.uuid4()),
        "name": "Ravi Kumar",
        "phone": "+919876543210",
        "upi_id": "ravi.kumar@upi",
        "platform": "swiggy",
        "vehicle_type": "bike",
        "micro_zone_id": "BLR_KORAMANGALA_NW",
        "tenure_weeks": 58,
        "trust_score": 0.74,
        "cold_start": False,
        "base_daily_mean": 560.0,
        "base_daily_std": 75.0,
        "peer_daily_mean": 530.0,
        "peer_daily_std": 85.0,
        "sample_size": 28,
        "coverage_tier": CoverageTierEnum.premium,
        "coverage_ratio": 0.86,
        "max_weekly_multiplier": 6.4,
        "weekly_premium_rate": 0.082,
        "risk_multiplier": 1.05,
        "trust_discount": 0.18,
        "disruption_profile": {6: 0.20, 7: 0.24, 8: 0.22, 9: 0.16, 10: 0.06, 11: 0.04, 12: 0.03, 1: 0.03, 2: 0.03, 3: 0.05, 4: 0.07, 5: 0.11},
        "disruption_types": ["rainfall", "flood"],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Ananya Iyer",
        "phone": "+919876543211",
        "upi_id": "ananya.iyer@upi",
        "platform": "zepto",
        "vehicle_type": "bike",
        "micro_zone_id": "BLR_KORAMANGALA_CENTRAL",
        "tenure_weeks": 41,
        "trust_score": 0.69,
        "cold_start": False,
        "base_daily_mean": 575.0,
        "base_daily_std": 78.0,
        "peer_daily_mean": 548.0,
        "peer_daily_std": 82.0,
        "sample_size": 26,
        "coverage_tier": CoverageTierEnum.standard,
        "coverage_ratio": 0.80,
        "max_weekly_multiplier": 6.2,
        "weekly_premium_rate": 0.079,
        "risk_multiplier": 1.08,
        "trust_discount": 0.14,
        "disruption_profile": {6: 0.17, 7: 0.22, 8: 0.21, 9: 0.15, 10: 0.06, 11: 0.04, 12: 0.03, 1: 0.03, 2: 0.03, 3: 0.05, 4: 0.07, 5: 0.10},
        "disruption_types": ["rainfall", "flood"],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Karthik Rao",
        "phone": "+919876543212",
        "upi_id": "karthik.rao@upi",
        "platform": "amazon",
        "vehicle_type": "bike",
        "micro_zone_id": "BLR_KORAMANGALA_SE",
        "tenure_weeks": 34,
        "trust_score": 0.56,
        "cold_start": False,
        "base_daily_mean": 620.0,
        "base_daily_std": 90.0,
        "peer_daily_mean": 575.0,
        "peer_daily_std": 92.0,
        "sample_size": 24,
        "coverage_tier": CoverageTierEnum.standard,
        "coverage_ratio": 0.78,
        "max_weekly_multiplier": 6.6,
        "weekly_premium_rate": 0.084,
        "risk_multiplier": 1.12,
        "trust_discount": 0.10,
        "disruption_profile": {6: 0.11, 7: 0.15, 8: 0.18, 9: 0.12, 10: 0.05, 11: 0.03, 12: 0.02, 1: 0.02, 2: 0.02, 3: 0.04, 4: 0.05, 5: 0.08},
        "disruption_types": ["rainfall", "flood"],
        "gaming_pattern": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Priya Sharma",
        "phone": "+919876543213",
        "upi_id": "priya.sharma@upi",
        "platform": "zomato",
        "vehicle_type": "cycle",
        "micro_zone_id": "PUN_KOTHRUD_W",
        "tenure_weeks": 20,
        "trust_score": 0.63,
        "cold_start": True,
        "base_daily_mean": 450.0,
        "base_daily_std": 62.0,
        "peer_daily_mean": 442.0,
        "peer_daily_std": 68.0,
        "sample_size": 18,
        "coverage_tier": CoverageTierEnum.basic,
        "coverage_ratio": 0.72,
        "max_weekly_multiplier": 5.3,
        "weekly_premium_rate": 0.061,
        "risk_multiplier": 1.02,
        "trust_discount": 0.08,
        "disruption_profile": {6: 0.09, 7: 0.19, 8: 0.21, 9: 0.11, 10: 0.04, 11: 0.03, 12: 0.02, 1: 0.02, 2: 0.02, 3: 0.03, 4: 0.05, 5: 0.07},
        "disruption_types": ["rainfall", "aqi"],
        "data_start_offset": 70,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Meera Joshi",
        "phone": "+919876543214",
        "upi_id": "meera.joshi@upi",
        "platform": "zepto",
        "vehicle_type": "cycle",
        "micro_zone_id": "PUN_KOTHRUD_CENTRAL",
        "tenure_weeks": 28,
        "trust_score": 0.68,
        "cold_start": False,
        "base_daily_mean": 470.0,
        "base_daily_std": 66.0,
        "peer_daily_mean": 458.0,
        "peer_daily_std": 72.0,
        "sample_size": 19,
        "coverage_tier": CoverageTierEnum.standard,
        "coverage_ratio": 0.76,
        "max_weekly_multiplier": 5.5,
        "weekly_premium_rate": 0.066,
        "risk_multiplier": 1.06,
        "trust_discount": 0.11,
        "disruption_profile": {6: 0.10, 7: 0.18, 8: 0.20, 9: 0.10, 10: 0.04, 11: 0.03, 12: 0.02, 1: 0.02, 2: 0.02, 3: 0.03, 4: 0.05, 5: 0.08},
        "disruption_types": ["rainfall", "aqi"],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Farhan Khan",
        "phone": "+919876543215",
        "upi_id": "farhan.khan@upi",
        "platform": "swiggy",
        "vehicle_type": "bike",
        "micro_zone_id": "PUN_KOTHRUD_SE",
        "tenure_weeks": 31,
        "trust_score": 0.59,
        "cold_start": False,
        "base_daily_mean": 490.0,
        "base_daily_std": 68.0,
        "peer_daily_mean": 470.0,
        "peer_daily_std": 74.0,
        "sample_size": 18,
        "coverage_tier": CoverageTierEnum.basic,
        "coverage_ratio": 0.74,
        "max_weekly_multiplier": 5.7,
        "weekly_premium_rate": 0.068,
        "risk_multiplier": 1.09,
        "trust_discount": 0.09,
        "disruption_profile": {6: 0.11, 7: 0.20, 8: 0.22, 9: 0.11, 10: 0.04, 11: 0.03, 12: 0.02, 1: 0.02, 2: 0.02, 3: 0.03, 4: 0.05, 5: 0.08},
        "disruption_types": ["rainfall", "aqi"],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Suresh Reddy",
        "phone": "+919876543216",
        "upi_id": "suresh.reddy@upi",
        "platform": "amazon",
        "vehicle_type": "bike",
        "micro_zone_id": "HYD_GACHIBOWLI_W",
        "tenure_weeks": 36,
        "trust_score": 0.53,
        "cold_start": False,
        "base_daily_mean": 610.0,
        "base_daily_std": 88.0,
        "peer_daily_mean": 575.0,
        "peer_daily_std": 94.0,
        "sample_size": 22,
        "coverage_tier": CoverageTierEnum.standard,
        "coverage_ratio": 0.77,
        "max_weekly_multiplier": 6.3,
        "weekly_premium_rate": 0.081,
        "risk_multiplier": 1.11,
        "trust_discount": 0.07,
        "disruption_profile": {6: 0.10, 7: 0.14, 8: 0.17, 9: 0.11, 10: 0.05, 11: 0.04, 12: 0.03, 1: 0.03, 2: 0.03, 3: 0.04, 4: 0.05, 5: 0.08},
        "disruption_types": ["rainfall", "curfew"],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Divya Nair",
        "phone": "+919876543217",
        "upi_id": "divya.nair@upi",
        "platform": "swiggy",
        "vehicle_type": "bike",
        "micro_zone_id": "HYD_GACHIBOWLI_CENTRAL",
        "tenure_weeks": 27,
        "trust_score": 0.66,
        "cold_start": False,
        "base_daily_mean": 630.0,
        "base_daily_std": 92.0,
        "peer_daily_mean": 584.0,
        "peer_daily_std": 96.0,
        "sample_size": 21,
        "coverage_tier": CoverageTierEnum.standard,
        "coverage_ratio": 0.79,
        "max_weekly_multiplier": 6.5,
        "weekly_premium_rate": 0.083,
        "risk_multiplier": 1.07,
        "trust_discount": 0.12,
        "disruption_profile": {6: 0.11, 7: 0.15, 8: 0.18, 9: 0.12, 10: 0.05, 11: 0.03, 12: 0.02, 1: 0.02, 2: 0.02, 3: 0.04, 4: 0.05, 5: 0.08},
        "disruption_types": ["rainfall", "curfew"],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Arjun Das",
        "phone": "+919876543218",
        "upi_id": "arjun.das@upi",
        "platform": "zomato",
        "vehicle_type": "cycle",
        "micro_zone_id": "HYD_GACHIBOWLI_E",
        "tenure_weeks": 29,
        "trust_score": 0.57,
        "cold_start": False,
        "base_daily_mean": 600.0,
        "base_daily_std": 86.0,
        "peer_daily_mean": 568.0,
        "peer_daily_std": 90.0,
        "sample_size": 21,
        "coverage_tier": CoverageTierEnum.basic,
        "coverage_ratio": 0.75,
        "max_weekly_multiplier": 6.1,
        "weekly_premium_rate": 0.079,
        "risk_multiplier": 1.10,
        "trust_discount": 0.09,
        "disruption_profile": {6: 0.10, 7: 0.13, 8: 0.16, 9: 0.10, 10: 0.05, 11: 0.03, 12: 0.02, 1: 0.02, 2: 0.02, 3: 0.03, 4: 0.05, 5: 0.07},
        "disruption_types": ["rainfall", "curfew"],
    },
]

ZONE_LOOKUP = {profile["micro_zone_id"]: profile for profile in WORKER_PROFILES}

SEED_WORKER_PHONES = [profile["phone"] for profile in WORKER_PROFILES]

SEED_ZONE_IDS = sorted({profile["micro_zone_id"] for profile in WORKER_PROFILES})

PEER_CLUSTERS = [
    {
        "micro_zone_id": profile["micro_zone_id"],
        "platform": profile["platform"],
        "vehicle_type": profile["vehicle_type"],
        "peer_daily_mean": profile["peer_daily_mean"],
        "peer_daily_std": profile["peer_daily_std"],
        "sample_size": profile["sample_size"],
    }
    for profile in WORKER_PROFILES
]

SEED_PAYMENT_METHOD = PaymentMethodEnum.upi

# ─────────────────────────────────────────────
# DAY OF WEEK MULTIPLIERS
# Source: Swiggy/Zomato public order volume reports
# ─────────────────────────────────────────────
DAY_MULTIPLIERS = {
    0: 0.88,   # Monday    — lowest demand
    1: 0.90,   # Tuesday
    2: 0.92,   # Wednesday
    3: 0.95,   # Thursday
    4: 1.10,   # Friday    — weekend lead-in
    5: 1.28,   # Saturday  — peak
    6: 1.22,   # Sunday    — peak
}

def get_disruption_prob(profile: dict, d: date) -> float:
    """Get disruption probability for a given date."""
    return profile["disruption_profile"].get(d.month, 0.05)


def generate_daily_income(
    profile: dict,
    d: date,
    is_disrupted: bool
) -> float:
    """
    Generate realistic daily income using Normal distribution.

    Normal days:
        income ~ N(base_mean × day_multiplier, std)

    Disrupted days:
        income ~ Beta(2, 5) × base_mean × day_multiplier
        Beta(2,5) has mean ~0.28 — worker earns some
        income but significantly reduced.
        Not zero because some workers still deliver
        in light rain / partial disruptions.
    """
    day_mult = DAY_MULTIPLIERS[d.weekday()]
    adjusted_mean = profile["base_daily_mean"] * day_mult

    if not is_disrupted:
        income = np.random.normal(
            loc=adjusted_mean,
            scale=profile["base_daily_std"]
        )
        # Clamp — income can't be negative or unrealistically high
        income = float(np.clip(income, 150.0, adjusted_mean * 2.0))
    else:
        # Beta distribution for disrupted income
        # Beta(2,5) → mean ~0.28, right-skewed toward low values
        beta_sample = np.random.beta(2, 5)

        if profile.get("gaming_pattern"):
            # Suresh drops more than peers on disruption days
            # Beta(1.5, 6) → mean ~0.20 — very low activity
            beta_sample = np.random.beta(1.5, 6)

        income = float(beta_sample * adjusted_mean)
        income = max(income, 0.0)

    return round(income, 2)


def generate_worker_income_rows(
    profile: dict,
    worker_id: str
) -> list[dict]:
    """
    Generate 84 daily income rows for one worker.
    Priya only gets last 14 days (data_start_offset=70).
    """
    rows = []
    data_start_offset = profile.get("data_start_offset", 0)
    active_dates = ALL_DATES[data_start_offset:]

    for d in active_dates:
        disruption_prob = get_disruption_prob(profile, d)
        is_disrupted = random.random() < disruption_prob

        daily_income = generate_daily_income(
            profile, d, is_disrupted
        )

        clean_income = daily_income if not is_disrupted else None

        rows.append({
            "id"            : str(uuid.uuid4()),
            "worker_id"     : worker_id,
            "date"          : d,
            "daily_income"  : daily_income,
            "disruption_day": is_disrupted,
            "clean_income"  : clean_income,
            "created_at"    : utcnow(),
        })

    return rows


def generate_peer_cluster_rows(cluster: dict) -> list[dict]:
    """
    Generate 12 weekly peer cluster stat rows.
    Each week gets a slightly varied peer average
    (seasonal drift using Normal noise).
    """
    rows = []
    for week_num in range(12):
        week_start = START_DATE + timedelta(weeks=week_num)

        # Small seasonal drift in peer income week over week
        seasonal_noise = np.random.normal(0, 20)
        peer_avg = round(
            cluster["peer_daily_mean"] * 6 + seasonal_noise,
            2
        )
        peer_variance = round(
            (cluster["peer_daily_std"] ** 2) + abs(seasonal_noise),
            2
        )

        rows.append({
            "id"                  : str(uuid.uuid4()),
            "micro_zone_id"       : cluster["micro_zone_id"],
            "platform"            : cluster["platform"],
            "vehicle_type"        : cluster["vehicle_type"],
            "week_start"          : week_start,
            "peer_avg_income"     : peer_avg,
            "peer_income_variance": peer_variance,
            "sample_size"         : cluster["sample_size"],
            "created_at"          : utcnow(),
        })

    return rows


def generate_disruption_rows(
    profile: dict,
    income_rows: list[dict]
) -> list[dict]:
    """
    For every disruption day in the income data,
    create a matching Disruption record in the
    disruptions table so trigger history exists.
    """
    rows = []
    disruption_types = profile["disruption_types"]

    for row in income_rows:
        if not row["disruption_day"]:
            continue

        # Pick disruption type — weighted toward first type
        weights = [0.7, 0.3] if len(disruption_types) > 1 else [1.0]
        d_type = random.choices(disruption_types, weights=weights)[0]

        # Severity: Beta(3,2) → mean ~0.6, skewed toward moderate-high
        severity = float(np.random.beta(3, 2))
        severity = float(round(float(np.clip(severity, 0.3, 0.95)), 3))

        is_catastrophic = severity > 0.9

        started_at = datetime.combine(
            row["date"],
            datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        ended_at = started_at + timedelta(hours=random.randint(4, 18))

        rows.append({
            "id"              : str(uuid.uuid4()),
            "zone_id"         : profile["micro_zone_id"],
            "disruption_type" : d_type,
            "severity"        : severity,
            "signal_source"   : "SEED_DATA",
            "is_confirmed"    : True,
            "is_catastrophic" : is_catastrophic,
            "started_at"      : started_at,
            "ended_at"        : ended_at,
            "created_at"      : utcnow(),
        })

    return rows


def generate_policy_row(profile: dict, worker_id: str) -> dict:
    weekly_baseline = profile["base_daily_mean"] * 6.0
    return {
        "id": str(uuid.uuid4()),
        "worker_id": worker_id,
        "coverage_tier": profile["coverage_tier"].value,
        "coverage_ratio": round(float(profile["coverage_ratio"]), 3),
        "max_weekly_coverage": round(weekly_baseline * float(profile["coverage_ratio"]), 2),
        "weekly_premium": round(weekly_baseline * float(profile["weekly_premium_rate"]), 2),
        "risk_multiplier": round(float(profile["risk_multiplier"]), 3),
        "trust_discount": round(float(profile["trust_discount"]), 3),
        "is_active": True,
        "valid_from": START_DATE - timedelta(days=7),
        "valid_to": END_DATE + timedelta(days=365),
        "created_at": utcnow(),
    }


def generate_location_trace_rows(profile: dict, worker_id: str, income_rows: list[dict]) -> list[dict]:
    zone_id = profile["micro_zone_id"]
    base_coords = zone_coordinates_for(zone_id) or (20.5937, 78.9629)
    parent_zone_id = parent_zone_for(zone_id)

    rows: list[dict] = []
    ordered_days = sorted(income_rows, key=lambda row: row["date"])

    for index, income_row in enumerate(ordered_days):
        day_start = datetime.combine(income_row["date"], datetime.min.time()).replace(tzinfo=timezone.utc)
        trace_offsets = [7.5, 15.0]
        if index % 6 == 0:
            trace_offsets.append(21.0)

        for trace_index, hours_after_midnight in enumerate(trace_offsets):
            drift_trace = bool(profile.get("gaming_pattern")) and trace_index == len(trace_offsets) - 1 and index % 4 == 0
            lat_shift = random.uniform(-0.0014, 0.0014) + (0.009 if drift_trace else 0.0)
            lon_shift = random.uniform(-0.0014, 0.0014) + (0.009 if drift_trace else 0.0)
            latitude = round(base_coords[0] + lat_shift, 6)
            longitude = round(base_coords[1] + lon_shift, 6)
            mapped = map_coordinates_to_zone(latitude, longitude)

            if mapped is None:
                latitude = round(base_coords[0] + random.uniform(-0.0012, 0.0012), 6)
                longitude = round(base_coords[1] + random.uniform(-0.0012, 0.0012), 6)
                mapped = map_coordinates_to_zone(latitude, longitude)

            rows.append({
                "id": str(uuid.uuid4()),
                "worker_id": worker_id,
                "latitude": latitude,
                "longitude": longitude,
                "accuracy_meters": round(random.uniform(10.0, 36.0), 1),
                "source": "browser_periodic",
                "mapped_parent_zone_id": (mapped or {}).get("parent_zone_id", parent_zone_id),
                "mapped_fine_zone_id": (mapped or {}).get("fine_zone_id", zone_id),
                "created_at": day_start + timedelta(hours=hours_after_midnight),
            })

    return rows


def _claim_status_for_profile(profile: dict, index: int, total_claims: int) -> ClaimStatusEnum:
    if index == 0:
        return ClaimStatusEnum.paid
    if index == total_claims - 1:
        return ClaimStatusEnum.pending if profile["trust_score"] >= 0.65 else ClaimStatusEnum.held
    if profile.get("gaming_pattern") or profile["trust_score"] < 0.6:
        return ClaimStatusEnum.held if index % 2 == 0 else ClaimStatusEnum.rejected
    return ClaimStatusEnum.rejected if index % 2 == 0 else ClaimStatusEnum.held


def generate_claim_rows(profile: dict, worker_id: str, policy_id: str, disruption_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    claims: list[dict] = []
    payouts: list[dict] = []
    if not disruption_rows:
        return claims, payouts

    ordered_disruptions = sorted(disruption_rows, key=lambda row: row["started_at"])
    if len(ordered_disruptions) >= 4:
        selected_indices = [0, len(ordered_disruptions) // 3, (2 * len(ordered_disruptions)) // 3, len(ordered_disruptions) - 1]
    elif len(ordered_disruptions) == 3:
        selected_indices = [0, 1, 2]
    else:
        selected_indices = list(range(len(ordered_disruptions)))

    selected_disruptions = [ordered_disruptions[index] for index in sorted(set(selected_indices))]

    for index, disruption in enumerate(selected_disruptions):
        status = _claim_status_for_profile(profile, index, len(selected_disruptions))
        severity = float(disruption["severity"])
        trust_score = float(profile["trust_score"])

        income_lost = round(profile["base_daily_mean"] * (1.2 + severity), 2)
        eligible_hours = round(4.0 + (2.25 * (1.0 - trust_score)) + (0.35 * index), 2)
        payout_amount = round(income_lost * float(profile["coverage_ratio"]) * (0.88 if status == ClaimStatusEnum.paid else 0.0), 2)
        baf_score = round(0.84 - (0.10 * index) - (0.08 if profile.get("gaming_pattern") else 0.0), 3)
        signal_confidence = round(max(0.52, 0.94 - (0.07 * index)), 3)
        behavior_confidence = round(max(0.38, 0.88 - (0.15 * index)), 3)
        unified_confidence = round((signal_confidence + behavior_confidence) / 2.0, 3)
        fraud_score = round((1.0 - signal_confidence) * 100.0, 2)
        fraud_band = "high" if fraud_score >= 75.0 else "medium" if fraud_score >= 55.0 else "low"
        spoofing_signals_fired = 0 if status == ClaimStatusEnum.paid else (4 if profile.get("gaming_pattern") else 2)
        audit_required = status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected}
        explanation = (
            f"Seeded suspicious history for {profile['name']} with repeated spoofing markers."
            if audit_required
            else f"Seeded low-risk claim for {profile['name']} with limited anomaly indicators."
        )

        claim_id = str(uuid.uuid4())
        claims.append({
            "id": claim_id,
            "worker_id": worker_id,
            "policy_id": policy_id,
            "disruption_id": disruption["id"],
            "status": status.value,
            "baf_score": baf_score,
            "payout_amount": payout_amount if status == ClaimStatusEnum.paid else None,
            "income_lost": income_lost,
            "eligible_hours": eligible_hours,
            "severity_smoothed": round(severity, 3),
            "signal_confidence": signal_confidence,
            "behavior_confidence": behavior_confidence,
            "unified_confidence": unified_confidence,
            "fraud_score": fraud_score,
            "fraud_band": fraud_band,
            "fraud_explanation": explanation,
            "fraud_explanation_confidence": 0.91 if audit_required else 0.74,
            "fraud_explanation_source": "seed_heuristic",
            "fraud_component_scores": {
                "signal_confidence_gap": round((1.0 - signal_confidence) * 100.0, 2),
                "behavior_confidence_gap": round((1.0 - behavior_confidence) * 100.0, 2),
                "spoofing_signals_fired": float(spoofing_signals_fired),
                "trust_penalty": round((1.0 - trust_score) * 100.0, 2),
            },
            "fraud_top_reasons": [
                "Seeded suspicious history" if audit_required else "Stable seeded profile",
                f"Signal confidence {signal_confidence:.2f}",
                f"Behavior confidence {behavior_confidence:.2f}",
            ],
            "spoofing_signals_fired": spoofing_signals_fired,
            "syndicate_flag": bool(profile.get("gaming_pattern")),
            "audit_required": audit_required,
            "audit_reason": "Seeded suspicious history" if audit_required else None,
            "created_at": disruption["started_at"] + timedelta(hours=2),
            "updated_at": disruption["started_at"] + timedelta(hours=2),
        })

        if status == ClaimStatusEnum.paid:
            payouts.append({
                "id": str(uuid.uuid4()),
                "claim_id": claim_id,
                "worker_id": worker_id,
                "amount": payout_amount,
                "payment_method": SEED_PAYMENT_METHOD.value,
                "payment_status": PaymentStatusEnum.completed.value,
                "razorpay_order_id": f"seed_{claim_id[:8]}",
                "initiated_at": disruption["started_at"] + timedelta(hours=3),
                "completed_at": disruption["started_at"] + timedelta(hours=3, minutes=5),
            })

    return claims, payouts


def seed(db: Session) -> None:
    """Main seed function. Clears seed data and repopulates all pipeline tables."""
    print("GigShield seed data generator")
    print("=" * 40)

    print("Clearing existing data...")
    existing_seed_worker_ids = [
        row.id for row in db.query(Worker.id).filter(Worker.phone.in_(SEED_WORKER_PHONES)).all()
    ]

    if existing_seed_worker_ids:
        db.query(Payout).filter(Payout.worker_id.in_(existing_seed_worker_ids)).delete(synchronize_session=False)
        db.query(Claim).filter(Claim.worker_id.in_(existing_seed_worker_ids)).delete(synchronize_session=False)
        db.query(WorkerLocationTrace).filter(WorkerLocationTrace.worker_id.in_(existing_seed_worker_ids)).delete(synchronize_session=False)
        db.query(Policy).filter(Policy.worker_id.in_(existing_seed_worker_ids)).delete(synchronize_session=False)
        db.query(WorkerDailyIncome).filter(WorkerDailyIncome.worker_id.in_(existing_seed_worker_ids)).delete(synchronize_session=False)
        db.query(Worker).filter(Worker.id.in_(existing_seed_worker_ids)).delete(synchronize_session=False)

    db.query(PeerClusterStats).delete()
    db.query(Disruption).filter(Disruption.signal_source == "SEED_DATA").delete()
    db.commit()

    all_income_rows: list[dict] = []
    all_disruption_rows: list[dict] = []
    all_peer_rows: list[dict] = []
    all_trace_rows: list[dict] = []
    all_policy_rows: list[dict] = []
    all_claim_rows: list[dict] = []
    all_payout_rows: list[dict] = []

    for profile in WORKER_PROFILES:
        print(f"\nGenerating data for {profile['name']}...")

        worker = Worker(
            id=profile["id"],
            name=profile["name"],
            phone=profile["phone"],
            upi_id=profile["upi_id"],
            platform=profile["platform"],
            vehicle_type=profile["vehicle_type"],
            micro_zone_id=profile["micro_zone_id"],
            tenure_weeks=profile["tenure_weeks"],
            avg_weekly_income=profile["base_daily_mean"] * 6,
            trust_score=profile["trust_score"],
            cold_start=profile["cold_start"],
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(worker)

        income_rows = generate_worker_income_rows(profile, profile["id"])
        disruption_rows = generate_disruption_rows(profile, income_rows)
        policy_row = generate_policy_row(profile, profile["id"])
        trace_rows = generate_location_trace_rows(profile, profile["id"], income_rows)
        claim_rows, payout_rows = generate_claim_rows(profile, profile["id"], policy_row["id"], disruption_rows)

        all_income_rows.extend(income_rows)
        all_disruption_rows.extend(disruption_rows)
        all_policy_rows.append(policy_row)
        all_trace_rows.extend(trace_rows)
        all_claim_rows.extend(claim_rows)
        all_payout_rows.extend(payout_rows)

        disrupted = sum(1 for row in income_rows if row["disruption_day"])
        clean = len(income_rows) - disrupted
        avg_clean = np.mean([row["daily_income"] for row in income_rows if not row["disruption_day"]]) if clean > 0 else 0

        print(f"  Days seeded    : {len(income_rows)}")
        print(f"  Clean days     : {clean}")
        print(f"  Disrupted days : {disrupted}")
        print(f"  Avg clean income/day : ₹{avg_clean:.0f}")
        print(f"  Expected weekly baseline : ₹{avg_clean * 6:.0f}")
        print(f"  Disruptions created : {len(disruption_rows)}")
        print(f"  Location traces   : {len(trace_rows)}")
        print(f"  Claims created    : {len(claim_rows)}")

    print("\nGenerating peer cluster stats...")
    for cluster in PEER_CLUSTERS:
        peer_rows = generate_peer_cluster_rows(cluster)
        all_peer_rows.extend(peer_rows)
        print(f"  {cluster['micro_zone_id']} : {len(peer_rows)} weeks seeded")

    db.flush()

    print("\nInserting into database...")
    db.bulk_insert_mappings(Policy, all_policy_rows)
    db.bulk_insert_mappings(WorkerDailyIncome, all_income_rows)
    db.bulk_insert_mappings(PeerClusterStats, all_peer_rows)
    db.bulk_insert_mappings(Disruption, all_disruption_rows)
    db.bulk_insert_mappings(WorkerLocationTrace, all_trace_rows)
    db.bulk_insert_mappings(Claim, all_claim_rows)
    db.bulk_insert_mappings(Payout, all_payout_rows)
    db.commit()

    print("\n" + "=" * 40)
    print("Seed complete.")
    print(f"  Workers inserted        : {len(WORKER_PROFILES)}")
    print(f"  Policies inserted       : {len(all_policy_rows)}")
    print(f"  Daily income rows       : {len(all_income_rows)}")
    print(f"  Peer cluster stat rows  : {len(all_peer_rows)}")
    print(f"  Disruption rows         : {len(all_disruption_rows)}")
    print(f"  Location trace rows     : {len(all_trace_rows)}")
    print(f"  Claim rows              : {len(all_claim_rows)}")
    print(f"  Payout rows             : {len(all_payout_rows)}")
    print("=" * 40)
    print("\nSeeded zones:")
    for profile in WORKER_PROFILES:
        print(f"  {profile['name']} — {profile['micro_zone_id']} — {profile['platform'].title()} — {profile['vehicle_type']}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    except Exception as e:
        print(f"\nSeed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()