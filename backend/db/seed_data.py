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

import uuid
import random
import numpy as np
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session

from database import SessionLocal
from models.worker import Worker
from models.worker_income import WorkerDailyIncome, PeerClusterStats
from models.disruption import Disruption

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
# WORKER PROFILES
# Based on real NITI Aayog / BCG gig worker data
# ─────────────────────────────────────────────
WORKER_PROFILES = [
    {
        # Established worker — happy path demo
        "id"             : str(uuid.uuid4()),
        "name"           : "Ravi Kumar",
        "phone"          : "+919876543210",
        "platform"       : "swiggy",
        "vehicle_type"   : "bike",
        "micro_zone_id"  : "BLR_KORAMANGALA_004",
        "tenure_weeks"   : 58,
        "trust_score"    : 0.74,
        "cold_start"     : False,

        # Income distribution parameters
        # Swiggy Bengaluru metro rider
        # Source: BCG Future of Work India 2023
        "base_daily_mean": 560.0,
        "base_daily_std" : 75.0,

        # Disruption profile — Bengaluru monsoon zone
        # Source: IMD Bengaluru historical 2019-2023
        "disruption_profile": {
            6: 0.18,   # June   — early monsoon
            7: 0.22,   # July   — peak monsoon
            8: 0.20,   # August — peak monsoon
            9: 0.14,   # Sept   — late monsoon
            10: 0.05,  # Oct    — post monsoon
            11: 0.03,  # Nov    — dry
            12: 0.02,  # Dec    — dry
            1: 0.02,   # Jan    — dry
            2: 0.02,   # Feb    — dry
            3: 0.04,   # Mar    — pre summer
            4: 0.06,   # Apr    — summer storms
            5: 0.10,   # May    — pre monsoon
        },
        "disruption_types": ["rainfall", "flood"],
    },
    {
        # New worker — cold start demo
        # Only 2 weeks of real history
        "id"             : str(uuid.uuid4()),
        "name"           : "Priya Sharma",
        "phone"          : "+919876543211",
        "platform"       : "zomato",
        "vehicle_type"   : "cycle",
        "micro_zone_id"  : "PUN_KOTHRUD_002",
        "tenure_weeks"   : 2,
        "trust_score"    : 0.6,
        "cold_start"     : True,

        # Zomato Pune — slightly lower than Bengaluru
        # Source: IDH Gig Worker Report 2022
        "base_daily_mean": 460.0,
        "base_daily_std" : 65.0,

        # Pune monsoon — less severe than Bengaluru
        "disruption_profile": {
            6: 0.08,
            7: 0.18,
            8: 0.20,
            9: 0.10,
            10: 0.03,
            11: 0.02,
            12: 0.02,
            1: 0.02,
            2: 0.02,
            3: 0.03,
            4: 0.05,
            5: 0.07,
        },
        "disruption_types": ["rainfall", "aqi"],

        # Priya only has data for last 14 days
        # Forces cold start + peer fallback in baseline engine
        "data_start_offset": 70,  # start 70 days in = last 14 days
    },
    {
        # Gaming worker — suspicious pattern demo
        "id"             : str(uuid.uuid4()),
        "name"           : "Suresh Reddy",
        "phone"          : "+919876543212",
        "platform"       : "amazon",
        "vehicle_type"   : "bike",
        "micro_zone_id"  : "HYD_GACHIBOWLI_007",
        "tenure_weeks"   : 34,
        "trust_score"    : 0.52,
        "cold_start"     : False,

        # Amazon Hyderabad — higher base (larger orders)
        # Source: EPFL Gig Economy India Study 2023
        "base_daily_mean": 620.0,
        "base_daily_std" : 90.0,

        # Hyderabad — moderate disruption
        "disruption_profile": {
            6: 0.10,
            7: 0.14,
            8: 0.18,
            9: 0.12,
            10: 0.04,
            11: 0.03,
            12: 0.02,
            1: 0.02,
            2: 0.02,
            3: 0.04,
            4: 0.05,
            5: 0.08,
        },
        "disruption_types": ["rainfall", "curfew"],

        # Suresh has suspicious pattern:
        # On disruption days his income drops MORE than peers
        # suggesting he stops working early (gaming)
        "gaming_pattern": True,
    },
]

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

# ─────────────────────────────────────────────
# PEER CLUSTER CONFIGURATIONS
# One per zone — used for peer_cluster_stats table
# ─────────────────────────────────────────────
PEER_CLUSTERS = [
    {
        "micro_zone_id" : "BLR_KORAMANGALA_004",
        "platform"      : "swiggy",
        "vehicle_type"  : "bike",
        # Peer avg slightly below Ravi (he's above average)
        "peer_daily_mean": 530.0,
        "peer_daily_std" : 85.0,
        "sample_size"    : 28,
    },
    {
        "micro_zone_id" : "PUN_KOTHRUD_002",
        "platform"      : "zomato",
        "vehicle_type"  : "cycle",
        # Peer avg close to Priya (she's average for her zone)
        "peer_daily_mean": 455.0,
        "peer_daily_std" : 70.0,
        "sample_size"    : 16,
    },
    {
        "micro_zone_id" : "HYD_GACHIBOWLI_007",
        "platform"      : "amazon",
        "vehicle_type"  : "bike",
        # Peer avg below Suresh (he earns more than peers)
        "peer_daily_mean": 580.0,
        "peer_daily_std" : 95.0,
        "sample_size"    : 22,
    },
]


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


def seed(db: Session) -> None:
    """
    Main seed function.
    Clears existing seed data and repopulates.
    Safe to run multiple times.
    """
    print("GigShield seed data generator")
    print("=" * 40)

    # ── Clear existing data in correct FK order ──
    print("Clearing existing data...")
    db.query(WorkerDailyIncome).delete()
    db.query(PeerClusterStats).delete()
    db.query(Disruption).filter(
        Disruption.signal_source == "SEED_DATA"
    ).delete()
    db.query(Worker).filter(
        Worker.phone.in_([
            "+919876543210",
            "+919876543211",
            "+919876543212",
        ])
    ).delete()
    db.commit()

    all_income_rows      = []
    all_disruption_rows  = []
    all_peer_rows        = []

    # ── Generate data for each worker ──
    for i, profile in enumerate(WORKER_PROFILES):
        print(f"\nGenerating data for {profile['name']}...")

        # 1. Create worker
        worker = Worker(
            id               = profile["id"],
            name             = profile["name"],
            phone            = profile["phone"],
            platform         = profile["platform"],
            vehicle_type     = profile["vehicle_type"],
            micro_zone_id    = profile["micro_zone_id"],
            tenure_weeks     = profile["tenure_weeks"],
            avg_weekly_income= profile["base_daily_mean"] * 6,
            trust_score      = profile["trust_score"],
            cold_start       = profile["cold_start"],
            created_at       = utcnow(),
            updated_at       = utcnow(),
        )
        db.add(worker)

        # 2. Generate daily income rows
        income_rows = generate_worker_income_rows(
            profile, profile["id"]
        )
        all_income_rows.extend(income_rows)

        # 3. Generate disruption rows from income data
        disruption_rows = generate_disruption_rows(
            profile, income_rows
        )
        all_disruption_rows.extend(disruption_rows)

        # Stats for verification
        disrupted = sum(1 for r in income_rows if r["disruption_day"])
        clean     = len(income_rows) - disrupted
        avg_clean = np.mean([
            r["daily_income"]
            for r in income_rows
            if not r["disruption_day"]
        ]) if clean > 0 else 0

        print(f"  Days seeded    : {len(income_rows)}")
        print(f"  Clean days     : {clean}")
        print(f"  Disrupted days : {disrupted}")
        print(f"  Avg clean income/day : ₹{avg_clean:.0f}")
        print(f"  Expected weekly baseline : "
              f"₹{avg_clean * 6:.0f}")
        print(f"  Disruptions created : {len(disruption_rows)}")

    # ── Generate peer cluster stats ──
    print("\nGenerating peer cluster stats...")
    for cluster in PEER_CLUSTERS:
        peer_rows = generate_peer_cluster_rows(cluster)
        all_peer_rows.extend(peer_rows)
        print(f"  {cluster['micro_zone_id']} : "
              f"{len(peer_rows)} weeks seeded")

    # Persist workers first so FK-dependent bulk inserts succeed.
    db.flush()

    # ── Bulk insert all rows ──
    print("\nInserting into database...")

    db.bulk_insert_mappings(WorkerDailyIncome, all_income_rows)
    db.bulk_insert_mappings(PeerClusterStats, all_peer_rows)
    db.bulk_insert_mappings(Disruption, all_disruption_rows)
    db.commit()

    # ── Final summary ──
    print("\n" + "=" * 40)
    print("Seed complete.")
    print(f"  Workers inserted        : {len(WORKER_PROFILES)}")
    print(f"  Daily income rows       : {len(all_income_rows)}")
    print(f"  Peer cluster stat rows  : {len(all_peer_rows)}")
    print(f"  Disruption rows         : {len(all_disruption_rows)}")
    print("=" * 40)
    print("\nTest workers:")
    print("  Ravi   — BLR_KORAMANGALA_004 — Swiggy  — established")
    print("  Priya  — PUN_KOTHRUD_002     — Zomato  — cold start")
    print("  Suresh — HYD_GACHIBOWLI_007  — Amazon  — gaming pattern")


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