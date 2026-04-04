"""Baseline income engine service stubs."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.worker import Worker
from models.worker_income import PeerClusterStats, WorkerDailyIncome


def _week_bucket(reference_end: date, d: date) -> int:
    return (reference_end - d).days // 7


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _find_peer_weekly_income(
    peer_rows: list[PeerClusterStats],
    reference_end: date,
    week_index: int,
    fallback_peer_avg: float,
) -> float:
    if not peer_rows:
        return fallback_peer_avg

    best = None
    best_distance = None
    for row in peer_rows:
        peer_idx = _week_bucket(reference_end, row.week_start)
        distance = abs(peer_idx - week_index)
        if best is None or distance < best_distance:
            best = row
            best_distance = distance

    if best is None:
        return fallback_peer_avg
    return float(best.peer_avg_income)


def _compute_window_summary(
    worker: Worker,
    db: Session,
    reference_end: date,
    window_days: int,
) -> dict:
    window_start = reference_end - timedelta(days=window_days - 1)

    all_rows = (
        db.query(WorkerDailyIncome)
        .filter(
            WorkerDailyIncome.worker_id == worker.id,
            WorkerDailyIncome.date >= window_start,
            WorkerDailyIncome.date <= reference_end,
        )
        .all()
    )

    peer_rows = (
        db.query(PeerClusterStats)
        .filter(
            PeerClusterStats.micro_zone_id == worker.micro_zone_id,
            PeerClusterStats.platform == worker.platform,
            PeerClusterStats.vehicle_type == worker.vehicle_type,
            PeerClusterStats.week_start >= window_start,
            PeerClusterStats.week_start <= reference_end,
        )
        .all()
    )

    fallback_peer_avg = _mean([float(r.peer_avg_income) for r in peer_rows])
    if fallback_peer_avg <= 0:
        fallback_peer_avg = max(float(worker.avg_weekly_income or 0.0), 1.0)

    rows_by_week: dict[int, list[WorkerDailyIncome]] = defaultdict(list)
    for row in all_rows:
        rows_by_week[_week_bucket(reference_end, row.date)].append(row)

    weeks_to_evaluate = max(window_days // 7, 1)
    week_estimates: list[float] = []
    clean_weekly_income: list[float] = []
    clean_weeks = 0
    used_peer_fallback = False

    for week_index in range(weeks_to_evaluate):
        week_rows = rows_by_week.get(week_index, [])
        if not week_rows:
            continue

        clean_rows = [r for r in week_rows if not r.disruption_day]
        clean_days = len(clean_rows)
        working_days = len(week_rows)

        if clean_days >= 3:
            clean_values = [
                float(r.clean_income) if r.clean_income is not None else float(r.daily_income)
                for r in clean_rows
            ]
            avg_clean_income = _mean(clean_values)
            expected_week_income = avg_clean_income * max(working_days, clean_days)
            week_estimates.append(expected_week_income)
            clean_weekly_income.append(expected_week_income)
            clean_weeks += 1
        else:
            used_peer_fallback = True
            week_estimates.append(
                _find_peer_weekly_income(
                    peer_rows=peer_rows,
                    reference_end=reference_end,
                    week_index=week_index,
                    fallback_peer_avg=fallback_peer_avg,
                )
            )

    if not week_estimates:
        week_estimates = [fallback_peer_avg]
        used_peer_fallback = True

    return {
        "week_estimates": week_estimates,
        "clean_weekly_income": clean_weekly_income,
        "clean_weeks": clean_weeks,
        "used_peer_fallback": used_peer_fallback,
        "peer_avg_income": fallback_peer_avg,
        "weeks_of_data": len(week_estimates),
    }


def compute_baseline_income(worker: Worker, db: Session) -> dict:
    """
    TO BE IMPLEMENTED BY: Idhant Singh

    Estimate counterfactual weekly income -
    what the worker would have earned with
    no disruptions.

    Logic:

    STEP 1 - Fetch rolling 8-week history:
    Query worker_daily_income for this worker,
    last 56 days, filter disruption_day=False.

    STEP 2 - Check data sufficiency:
    Count clean days per week.
    if clean_days_in_any_week < 3:
        use peer_cluster_stats fallback for that week
    if total clean_weeks < 4:
        widen window to 12 weeks (84 days)

    STEP 3 - Reconstruct full week income:
    Use uniform day_weight = 1/7 for all days.
    expected_week_income =
        sum(clean_daily_income / day_weight)
        x sum(day_weights for worker's working days)

    STEP 4 - Apply worker productivity factor:
    if worker.tenure_weeks < 8:
        baseline = peer_avg_income
                   x min(worker.tenure_weeks / 8, 1.0)
    else:
        worker_factor =
            mean(worker clean weekly income last 8 weeks)
            / peer_avg_income
        baseline = peer_avg_income x worker_factor

    STEP 5 - Update worker.avg_weekly_income = baseline
    Save to DB.

    Returns dict with keys:
    baseline_income (float),
    confidence (1.0 if individual, 0.6 if peer_fallback),
    data_source ("individual" or "peer_fallback"),
    weeks_of_data (int)
    """
    reference_end = (
        db.query(func.max(WorkerDailyIncome.date))
        .filter(WorkerDailyIncome.worker_id == worker.id)
        .scalar()
    )

    if reference_end is None:
        baseline = float(worker.avg_weekly_income or 0.0)
        worker.avg_weekly_income = baseline
        db.add(worker)
        db.commit()
        return {
            "baseline_income": round(baseline, 2),
            "confidence": 0.6,
            "data_source": "peer_fallback",
            "weeks_of_data": 0,
        }

    summary = _compute_window_summary(worker=worker, db=db, reference_end=reference_end, window_days=56)
    if summary["clean_weeks"] < 4:
        summary = _compute_window_summary(worker=worker, db=db, reference_end=reference_end, window_days=84)

    peer_avg_income = float(summary["peer_avg_income"])
    worker_clean_mean = _mean(summary["clean_weekly_income"])

    if worker.tenure_weeks < 8:
        baseline = peer_avg_income * min(max(worker.tenure_weeks, 0) / 8.0, 1.0)
        data_source = "peer_fallback"
        confidence = 0.6
    else:
        if peer_avg_income > 0:
            worker_factor = worker_clean_mean / peer_avg_income if worker_clean_mean > 0 else 1.0
        else:
            worker_factor = 1.0
        baseline = peer_avg_income * worker_factor
        data_source = "peer_fallback" if summary["used_peer_fallback"] else "individual"
        confidence = 0.6 if summary["used_peer_fallback"] else 1.0

    if baseline <= 0:
        baseline = _mean(summary["week_estimates"])

    baseline = float(round(max(baseline, 0.0), 2))
    worker.avg_weekly_income = baseline
    db.add(worker)
    db.commit()

    return {
        "baseline_income": baseline,
        "confidence": confidence,
        "data_source": data_source,
        "weeks_of_data": int(summary["weeks_of_data"]),
    }
