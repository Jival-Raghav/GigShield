"""Admin analytics service functions."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.payout import Payout
from models.worker import Worker
from services import risk_model

logger = logging.getLogger(__name__)


def _run_with_timeout(callable_fn, *, timeout_seconds: float):
    if timeout_seconds <= 0:
        return callable_fn()

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(callable_fn)
    try:
        return future.result(timeout=timeout_seconds)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _build_fast_zone_series(zone_id: str, expected_disruption_days: float, expected_severity: float, *, days: int = 7) -> list[dict]:
    start_date = datetime.now(timezone.utc).date()
    series: list[dict] = []
    for day_offset in range(days):
        forecast_date = (start_date + timedelta(days=day_offset)).isoformat()
        weekend_boost = 0.08 if (start_date + timedelta(days=day_offset)).weekday() >= 5 else 0.0
        daily_multiplier = 1.0 + weekend_boost
        projected_disruption_days = min(7.0, expected_disruption_days * daily_multiplier)
        projected_severity = min(1.0, expected_severity * (0.95 + weekend_boost))
        series.append(
            {
                "zone_id": zone_id,
                "forecast_date": forecast_date,
                "day_offset": day_offset,
                "signal_pressure": 0.0,
                "holiday_active": False,
                "windspeed_10m_max_kph": 0.0,
                "precipitation_sum_mm": 0.0,
                "news_risk": 0.0,
                "fire_risk": 0.0,
                "projected_disruption_days": round(projected_disruption_days, 3),
                "projected_severity": round(projected_severity, 3),
                "forecast_confidence": 0.55,
            }
        )
    return series


def get_dashboard_metrics(db: Session) -> dict:
    """Aggregate insurer dashboard KPIs for current day and week."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    forecast_window_start = now - timedelta(days=28)

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

    active_zone_rows = (
        db.query(Worker.micro_zone_id, func.count(Policy.id))
        .join(Worker, Worker.id == Policy.worker_id)
        .filter(Policy.is_active.is_(True))
        .group_by(Worker.micro_zone_id)
        .all()
    )

    forecast_zones: list[dict] = []
    zone_forecast_7d: list[dict] = []
    forecast_claims_total = 0.0
    forecast_payout_total = 0.0
    forecast_confidence_values: list[float] = []

    forecast_mode = settings.admin_forecast_mode.strip().lower()
    if forecast_mode not in {"fast", "ml", "hybrid"}:
        forecast_mode = "hybrid"

    for zone_id, active_policy_count in active_zone_rows:
        recent_claim_count = (
            db.query(func.count(Claim.id))
            .join(Worker, Worker.id == Claim.worker_id)
            .filter(Worker.micro_zone_id == zone_id, Claim.created_at >= forecast_window_start)
            .scalar()
            or 0
        )
        recent_payout_total = (
            db.query(func.coalesce(func.sum(Payout.amount), 0.0))
            .join(Claim, Claim.id == Payout.claim_id)
            .join(Worker, Worker.id == Claim.worker_id)
            .filter(Worker.micro_zone_id == zone_id, Payout.completed_at.is_not(None), Payout.completed_at >= forecast_window_start)
            .scalar()
            or 0.0
        )

        # Keep dashboard fast by using historical signal projection only.
        historical_disruption_count = (
            db.query(func.count(Disruption.id))
            .filter(Disruption.zone_id == zone_id, Disruption.created_at >= forecast_window_start)
            .scalar()
            or 0
        )
        expected_disruption_days = min(7.0, float(historical_disruption_count) / 4.0)
        expected_severity = min(1.0, 0.35 + (float(historical_disruption_count) / 20.0))

        model_confidence = 0.65 if active_policy_count else 0.0
        if forecast_mode in {"ml", "hybrid"}:
            try:
                ml_risk = _run_with_timeout(
                    lambda: risk_model.estimate_weekly_risk(zone_id=zone_id, db=db),
                    timeout_seconds=float(settings.admin_forecast_ml_timeout_seconds),
                )
                if isinstance(ml_risk, dict):
                    expected_disruption_days = float(ml_risk.get("expected_disruption_days", expected_disruption_days))
                    expected_severity = float(ml_risk.get("expected_severity", expected_severity))
                    model_confidence = float(ml_risk.get("model_confidence", model_confidence))
            except TimeoutError:
                logger.warning(
                    "Admin ML forecast timed out for zone %s in mode=%s. Using fast fallback.",
                    zone_id,
                    forecast_mode,
                )
            except Exception as exc:
                logger.warning(
                    "Admin ML forecast failed for zone %s in mode=%s: %s. Using fast fallback.",
                    zone_id,
                    forecast_mode,
                    exc,
                )

        projection_multiplier = 0.55 + expected_severity + (expected_disruption_days / 7.0)
        projected_claims = max(0.0, (float(recent_claim_count) / 4.0) * projection_multiplier)
        projected_payout = max(0.0, (float(recent_payout_total) / 4.0) * projection_multiplier)

        forecast_confidence = max(0.0, min(1.0, model_confidence))
        forecast_confidence_values.append(forecast_confidence)
        forecast_claims_total += projected_claims
        forecast_payout_total += projected_payout

        forecast_zones.append(
            {
                "zone_id": zone_id,
                "active_policy_count": int(active_policy_count or 0),
                "expected_disruption_days": round(expected_disruption_days, 2),
                "expected_severity": round(expected_severity, 2),
                "projected_claims_next_week": round(projected_claims, 2),
                "projected_payout_next_week": round(projected_payout, 2),
                "forecast_confidence": round(forecast_confidence, 3),
            }
        )

        fallback_series = _build_fast_zone_series(
            zone_id=zone_id,
            expected_disruption_days=expected_disruption_days,
            expected_severity=expected_severity,
            days=7,
        )

        zone_series = fallback_series
        if forecast_mode in {"ml", "hybrid"}:
            try:
                ml_series = _run_with_timeout(
                    lambda: risk_model.forecast_zone_risk_series(zone_id=zone_id, db=db, days=7),
                    timeout_seconds=float(settings.admin_forecast_ml_timeout_seconds),
                )
                if isinstance(ml_series, list) and ml_series:
                    zone_series = ml_series
            except TimeoutError:
                logger.warning(
                    "Admin ML 7-day series timed out for zone %s in mode=%s. Using fast fallback.",
                    zone_id,
                    forecast_mode,
                )
            except Exception as exc:
                logger.warning(
                    "Admin ML 7-day series failed for zone %s in mode=%s: %s. Using fast fallback.",
                    zone_id,
                    forecast_mode,
                    exc,
                )

        zone_forecast_7d.append({"zone_id": zone_id, "forecast": zone_series})

    forecast_zones.sort(key=lambda item: item["projected_claims_next_week"], reverse=True)
    top_zone = forecast_zones[0] if forecast_zones else None
    average_forecast_confidence = sum(forecast_confidence_values) / len(forecast_confidence_values) if forecast_confidence_values else 0.0

    return {
        "total_active_policies": int(total_active_policies),
        "total_claims_today": int(total_claims_today),
        "total_payouts_today": payout_today,
        "claims_pending_audit": int(claims_pending_audit),
        "active_disruptions": int(active_disruptions),
        "avg_baf_score": float(avg_baf_score),
        "loss_ratio": float(loss_ratio),
        "projected_claims_next_week": round(forecast_claims_total, 2),
        "projected_payout_next_week": round(forecast_payout_total, 2),
        "forecast_confidence": round(average_forecast_confidence, 3),
        "top_risk_zone": top_zone["zone_id"] if top_zone else None,
        "top_risk_zone_projected_claims": top_zone["projected_claims_next_week"] if top_zone else 0.0,
        "top_risk_zone_projected_payout": top_zone["projected_payout_next_week"] if top_zone else 0.0,
        "top_risk_zones": forecast_zones[:5],
        "zone_forecast_7d": zone_forecast_7d,
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
