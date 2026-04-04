"""Payout engine service functions."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, object_session

from models.claim import Claim
from models.disruption import Disruption
from models.policy import Policy
from models.worker import PlatformEnum, Worker
from models.worker_income import PeerClusterStats, WorkerDailyIncome
from services import baseline_engine


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _overlap_hours(start: datetime, end: datetime, window_start_hour: int, window_end_hour: int) -> float:
    """Calculate overlap between [start, end] and a daily hour window in UTC."""
    if end <= start:
        return 0.0

    total = 0.0
    cursor = start
    while cursor < end:
        day_start = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
        win_start = day_start + timedelta(hours=window_start_hour)
        win_end = day_start + timedelta(hours=window_end_hour)

        segment_start = max(cursor, win_start)
        segment_end = min(end, win_end)
        if segment_end > segment_start:
            total += (segment_end - segment_start).total_seconds() / 3600.0

        cursor = day_start + timedelta(days=1)

    return max(total, 0.0)


def _time_weighted_severity(raw_severity: float, disruption: Disruption) -> tuple[float, float]:
    """Adjust severity by overlap with prime gig working windows.

    Returns (severity_smoothed, effective_overlap_hours).
    """
    start_at = disruption.started_at
    end_at = disruption.ended_at or (start_at + timedelta(hours=1))
    total_hours = max((end_at - start_at).total_seconds() / 3600.0, 0.25)

    lunch_overlap = _overlap_hours(start_at, end_at, 11, 15)
    dinner_overlap = _overlap_hours(start_at, end_at, 18, 23)
    prime_overlap = lunch_overlap + dinner_overlap

    overlap_ratio = _clamp(prime_overlap / max(total_hours, 0.25), 0.0, 1.0)
    peak_bonus = _clamp(dinner_overlap / max(prime_overlap, 0.25), 0.0, 1.0)

    time_factor = _clamp(0.25 + (0.75 * overlap_ratio) + (0.15 * peak_bonus), 0.2, 1.15)
    severity_smoothed = _clamp(float(raw_severity) * time_factor, 0.0, 1.0)

    return severity_smoothed, prime_overlap


def _latest_peer_weekly_avg(worker: Worker, ref_date, db: Session) -> float:
    peer_row = (
        db.query(PeerClusterStats)
        .filter(
            PeerClusterStats.micro_zone_id == worker.micro_zone_id,
            PeerClusterStats.platform == worker.platform,
            PeerClusterStats.vehicle_type == worker.vehicle_type,
            PeerClusterStats.week_start <= ref_date,
        )
        .order_by(PeerClusterStats.week_start.desc())
        .first()
    )
    if peer_row is not None and float(peer_row.peer_avg_income) > 0:
        return float(peer_row.peer_avg_income)
    return max(float(worker.avg_weekly_income or 0.0), 1.0)


def _collect_activity_metrics(worker: Worker, disruption: Disruption, db: Session) -> dict:
    disruption_date = disruption.started_at.date()
    history_start = disruption_date - timedelta(days=56)

    rows = (
        db.query(WorkerDailyIncome)
        .filter(
            WorkerDailyIncome.worker_id == worker.id,
            WorkerDailyIncome.date >= history_start,
            WorkerDailyIncome.date <= disruption_date,
        )
        .all()
    )

    clean_rows = [r for r in rows if not r.disruption_day]
    clean_daily_values = [
        float(r.clean_income) if r.clean_income is not None else float(r.daily_income)
        for r in clean_rows
    ]
    activity_normal = _mean(clean_daily_values)

    during_rows = [r for r in rows if r.disruption_day and r.date == disruption_date]
    if during_rows:
        activity_during = _mean([float(r.daily_income) for r in during_rows])
    else:
        proxy_ratio = max(0.2, 1.0 - float(disruption.severity))
        activity_during = activity_normal * proxy_ratio

    recent_14_rows = [r for r in rows if r.date >= disruption_date - timedelta(days=13)]
    avg_activity_14d = _mean([float(r.daily_income) for r in recent_14_rows])

    peer_weekly_avg = _latest_peer_weekly_avg(worker=worker, ref_date=disruption_date, db=db)
    peer_daily_avg = peer_weekly_avg / 6.0

    acceptance_rate_normal = _clamp(0.55 + (float(worker.trust_score) * 0.25), 0.35, 0.9)
    base_ratio = activity_during / max(activity_normal, 0.01)
    acceptance_rate_during = _clamp(acceptance_rate_normal * base_ratio, 0.05, 1.0)

    online_hours = _clamp(8.0 * (0.7 + base_ratio * 0.6), 0.5, 12.0)
    peer_avg_hours = 8.0

    return {
        "activity_normal": activity_normal,
        "activity_during": activity_during,
        "avg_activity_14d": avg_activity_14d,
        "peer_daily_avg": peer_daily_avg,
        "acceptance_rate_normal": acceptance_rate_normal,
        "acceptance_rate_during": acceptance_rate_during,
        "online_hours": online_hours,
        "peer_avg_hours": peer_avg_hours,
    }


def compute_baf(worker: Worker, claim: Claim, disruption: Disruption, db: Session) -> float:
    """Compute Behavior Adjustment Factor (BAF) for the claim."""
    metrics = _collect_activity_metrics(worker=worker, disruption=disruption, db=db)

    peer_ratio = _clamp(metrics["activity_during"] / max(metrics["peer_daily_avg"], 0.01), 0.0, 1.2)

    acceptance_rate_normal = metrics["acceptance_rate_normal"]
    acceptance_rate_during = metrics["acceptance_rate_during"]
    activity_score = acceptance_rate_during / max(acceptance_rate_normal, 0.01)
    if activity_score <= 0:
        activity_score = 0.7

    if activity_score < 0.6 and metrics["online_hours"] > metrics["peer_avg_hours"]:
        activity_score *= 0.85
    activity_score = _clamp(activity_score)

    behavior_drop_ratio = metrics["activity_during"] / max(
        metrics["activity_normal"],
        max(0.01, 0.1 * metrics["avg_activity_14d"]),
    )
    temporal_score = _clamp(1.0 / (1.0 + math.exp(-5.0 * (behavior_drop_ratio - 1.0))))

    low_effort_count = 0
    recent_claims = (
        db.query(Claim)
        .filter(Claim.worker_id == worker.id)
        .order_by(Claim.created_at.desc())
        .limit(5)
        .all()
    )
    for prev in recent_claims:
        prev_activity = float(prev.behavior_confidence) if prev.behavior_confidence is not None else 0.7
        prev_peer = float(prev.signal_confidence) if prev.signal_confidence is not None else 0.7
        if prev_activity < 0.4 and prev_peer < 0.5:
            low_effort_count += 1

    if activity_score < 0.4 and peer_ratio < 0.5:
        low_effort_count += 1

    if low_effort_count >= 3:
        penalty = 0.6
    elif low_effort_count == 2:
        penalty = 0.8
    else:
        penalty = 1.0

    if disruption.is_catastrophic:
        catastrophic_baf = 0.7 * float(disruption.severity) + 0.2 * temporal_score + 0.1 * activity_score
        catastrophic_baf = max(catastrophic_baf, 0.70)
        return round(_clamp(catastrophic_baf * penalty), 4)

    baf_raw = 0.4 * peer_ratio + 0.35 * activity_score + 0.25 * temporal_score

    trust = float(worker.trust_score)
    if trust > 0.8:
        floor = 0.30
    elif trust > 0.6:
        floor = 0.25
    elif trust > 0.4:
        floor = 0.20
    else:
        floor = 0.10

    baf = max(baf_raw, floor)
    final_baf = _clamp(baf * penalty)
    return round(final_baf, 4)


def calculate_payout(
    worker: Worker,
    claim: Claim,
    policy: Policy,
    disruption: Disruption,
    baf_score: float,
) -> dict:
    """Calculate payout amount from baseline loss, policy and BAF."""
    db_session = object_session(worker)
    if db_session is not None:
        baseline = baseline_engine.compute_baseline_income(worker=worker, db=db_session)
        baseline_income = float(baseline.get("baseline_income", worker.avg_weekly_income or 0.0))
    else:
        baseline_income = float(worker.avg_weekly_income or 0.0)

    hourly_income = baseline_income / (6.0 * 8.0)

    platform_hourly_rate = {
        PlatformEnum.swiggy: 95.0,
        PlatformEnum.zomato: 92.0,
        PlatformEnum.amazon: 110.0,
        PlatformEnum.zepto: 100.0,
    }
    hourly_rate = platform_hourly_rate.get(worker.platform, 95.0)
    worker_avg_daily_hours = baseline_income / max(hourly_rate * 6.0, 1.0)

    shift_overlap_hours = 8.0
    platform_max_hours = {
        PlatformEnum.swiggy: 10.0,
        PlatformEnum.zomato: 10.0,
        PlatformEnum.amazon: 12.0,
        PlatformEnum.zepto: 10.0,
    }.get(worker.platform, 10.0)

    severity_smoothed, prime_overlap_hours = _time_weighted_severity(float(disruption.severity), disruption)
    effective_overlap_hours = min(shift_overlap_hours, max(prime_overlap_hours, 0.5))

    eligible_hours = min(effective_overlap_hours, worker_avg_daily_hours, platform_max_hours)
    eligible_hours = max(0.0, eligible_hours)

    income_lost = hourly_income * eligible_hours * severity_smoothed

    # Weekly cap is applied by the weekly settlement engine across all approved claims.
    adjusted_payout = income_lost * float(policy.coverage_ratio) * _clamp(float(baf_score), 0.0, 1.0)

    return {
        "income_lost": round(max(income_lost, 0.0), 2),
        "eligible_hours": round(eligible_hours, 2),
        "severity_smoothed": round(severity_smoothed, 3),
        "hourly_income": round(max(hourly_income, 0.0), 2),
        "uncapped_payout": round(max(adjusted_payout, 0.0), 2),
        "adjusted_payout": round(max(adjusted_payout, 0.0), 2),
    }
