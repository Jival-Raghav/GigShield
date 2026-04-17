"""Risk modeling helpers for premium pricing."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from config import settings
from mock_apis import get_aqi, get_rainfall
from services.intelligence_signals import get_zone_intelligence_series, get_zone_intelligence_snapshot

from sqlalchemy.orm import Session

from models.disruption import Disruption
from models.worker import Worker

logger = logging.getLogger(__name__)

FEATURE_COLUMNS_DEFAULT = [
    "week_of_year",
    "month",
    "zone_risk_bucket",
    "disruptions_last_4_weeks",
    "avg_severity_last_4_weeks",
    "disruptions_same_month_last_year",
    "platform_volatility_index",
]

PLATFORM_VOLATILITY = {
    "swiggy": 1.1,
    "zomato": 1.1,
    "amazon": 1.0,
    "zepto": 1.2,
}

_MODEL_CACHE: dict[str, object] = {
    "initialized": False,
    "probability_model": None,
    "severity_model": None,
    "feature_columns": FEATURE_COLUMNS_DEFAULT,
}


def _family_suffix() -> str:
    family = settings.risk_forecast_model_family
    if family in {"xgboost", "lightgbm", "gradient_boosting"}:
        return family
    return "gradient_boosting"


def _week_start(dt: datetime) -> datetime:
    base = dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return base - timedelta(days=base.weekday())


def _zone_risk_bucket(zone_id: str) -> int:
    zone = zone_id.lower()
    if any(token in zone for token in ["high", "flood", "coastal", "river", "dense", "central"]):
        return 2
    if any(token in zone for token in ["low", "suburb", "outskirts", "rural"]):
        return 0
    return 1


def _signal_pressure(zone_id: str) -> float:
    rainfall = get_rainfall(zone_id)
    aqi = get_aqi(zone_id)
    intelligence = get_zone_intelligence_snapshot(zone_id)
    rainfall_mm = float(rainfall.get("rainfall_mm_per_hr", 0.0))
    aqi_value = float(aqi.get("aqi", 0.0))
    rainfall_score = min(rainfall_mm / 100.0, 1.0)
    aqi_score = min(max(aqi_value - 100.0, 0.0) / 400.0, 1.0)
    intelligence_score = float(intelligence.get("signal_pressure", 0.0))
    return float(np.clip((0.4 * rainfall_score) + (0.3 * aqi_score) + (0.3 * intelligence_score), 0.0, 1.0))


def _platform_volatility_index(zone_id: str, db: Session) -> float:
    workers = db.query(Worker).filter(Worker.micro_zone_id == zone_id).all()
    if not workers:
        return 1.1

    counts: dict[str, int] = defaultdict(int)
    for worker in workers:
        counts[worker.platform.value.lower()] += 1

    platform = max(counts, key=counts.get)
    return float(PLATFORM_VOLATILITY.get(platform, 1.1))


def _month_bounds_last_year(now: datetime) -> tuple[datetime, datetime]:
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_last_year = month_start.replace(year=month_start.year - 1)
    if start_last_year.month == 12:
        end_last_year = start_last_year.replace(year=start_last_year.year + 1, month=1)
    else:
        end_last_year = start_last_year.replace(month=start_last_year.month + 1)
    return start_last_year, end_last_year


def _build_live_features(zone_id: str, db: Session, now: datetime) -> tuple[dict, int]:
    four_weeks_ago = now - timedelta(weeks=4)
    rows_4w = (
        db.query(Disruption)
        .filter(
            Disruption.zone_id == zone_id,
            Disruption.started_at >= four_weeks_ago,
            Disruption.started_at <= now,
        )
        .all()
    )

    disruptions_last_4_weeks = len(rows_4w)
    if rows_4w:
        avg_severity_last_4_weeks = float(np.mean([float(row.severity) for row in rows_4w]))
    else:
        avg_severity_last_4_weeks = _signal_pressure(zone_id)

    month_start_last_year, month_end_last_year = _month_bounds_last_year(now)
    same_month_last_year_rows = (
        db.query(Disruption)
        .filter(
            Disruption.zone_id == zone_id,
            Disruption.started_at >= month_start_last_year,
            Disruption.started_at < month_end_last_year,
        )
        .all()
    )

    history_window = now - timedelta(days=84)
    recent_rows = (
        db.query(Disruption)
        .filter(
            Disruption.zone_id == zone_id,
            Disruption.started_at >= history_window,
            Disruption.started_at <= now,
        )
        .all()
    )
    data_weeks = len({_week_start(row.started_at) for row in recent_rows})

    return (
        {
            "week_of_year": int(now.strftime("%V")),
            "month": int(now.month),
            "zone_risk_bucket": _zone_risk_bucket(zone_id),
            "disruptions_last_4_weeks": int(disruptions_last_4_weeks),
            "avg_severity_last_4_weeks": float(np.clip(avg_severity_last_4_weeks, 0.0, 1.0)),
            "disruptions_same_month_last_year": int(len(same_month_last_year_rows)),
            "platform_volatility_index": _platform_volatility_index(zone_id, db),
        },
        data_weeks,
    )


def _statistical_fallback(zone_id: str, db: Session) -> dict:
    """Statistical fallback used when model artifacts are unavailable."""
    logger.warning("Using mock risk fallback for zone %s.", zone_id)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=84)

    rows = (
        db.query(Disruption)
        .filter(
            Disruption.zone_id == zone_id,
            Disruption.started_at >= window_start,
        )
        .all()
    )

    if not rows:
        return {
            "expected_disruption_days": 1.5,
            "expected_severity": 0.45,
            "data_weeks": 0,
            "used_fallback": True,
            "model_confidence": 0.0,
        }

    current_week_start = _week_start(now)
    ordered_weeks = [current_week_start - timedelta(weeks=i) for i in range(11, -1, -1)]

    disruptions_by_week: dict[datetime, list[Disruption]] = defaultdict(list)
    for row in rows:
        wk = _week_start(row.started_at)
        disruptions_by_week[wk].append(row)

    weeks_with_data = len(disruptions_by_week)
    if weeks_with_data < 4:
        return {
            "expected_disruption_days": 1.5,
            "expected_severity": 0.45,
            "data_weeks": weeks_with_data,
            "used_fallback": True,
            "model_confidence": 0.0,
        }

    weighted_days_num = 0.0
    weighted_days_den = 0.0
    weighted_sev_num = 0.0
    weighted_sev_den = 0.0

    recent_cutoff = current_week_start - timedelta(weeks=3)

    for week in ordered_weeks:
        week_rows = disruptions_by_week.get(week, [])
        weight = 1.5 if week >= recent_cutoff else 1.0

        disruption_days = len({r.started_at.date() for r in week_rows})
        weighted_days_num += disruption_days * weight
        weighted_days_den += weight

        count = len(week_rows)
        if count > 0:
            avg_severity = sum(float(r.severity) for r in week_rows) / count
            weighted_sev_num += avg_severity * count * weight
            weighted_sev_den += count * weight

    expected_disruption_days = weighted_days_num / weighted_days_den if weighted_days_den > 0 else 1.5
    expected_severity = weighted_sev_num / weighted_sev_den if weighted_sev_den > 0 else 0.45

    return {
        "expected_disruption_days": round(max(expected_disruption_days, 0.0), 3),
        "expected_severity": round(max(min(expected_severity, 1.0), 0.0), 3),
        "data_weeks": weeks_with_data,
        "used_fallback": True,
        "model_confidence": 0.0,
    }


def _load_models_once() -> tuple[object | None, object | None, list[str]]:
    if _MODEL_CACHE["initialized"]:
        return (
            _MODEL_CACHE["probability_model"],
            _MODEL_CACHE["severity_model"],
            _MODEL_CACHE["feature_columns"],
        )

    _MODEL_CACHE["initialized"] = True

    ml_dir = Path(__file__).resolve().parents[1] / "ml"
    family = _family_suffix()
    candidate_suffixes = [family]
    if family != "gradient_boosting":
        candidate_suffixes.append("gradient_boosting")

    probability_model_path = None
    severity_model_path = None
    for suffix in candidate_suffixes:
        prob_path = ml_dir / ("risk_probability_model.joblib" if suffix == "gradient_boosting" else f"risk_probability_model_{suffix}.joblib")
        sev_path = ml_dir / ("risk_severity_model.joblib" if suffix == "gradient_boosting" else f"risk_severity_model_{suffix}.joblib")
        if prob_path.exists() and sev_path.exists():
            probability_model_path = prob_path
            severity_model_path = sev_path
            break

    feature_columns_path = ml_dir / "feature_columns.json"

    if not (probability_model_path and severity_model_path and feature_columns_path.exists()):
        logger.warning("Risk model artifacts missing in %s. Falling back to statistical estimate.", ml_dir)
        return None, None, FEATURE_COLUMNS_DEFAULT

    try:
        import joblib

        with feature_columns_path.open("r", encoding="utf-8") as feature_file:
            feature_columns = json.load(feature_file)

        probability_model = joblib.load(probability_model_path)
        severity_model = joblib.load(severity_model_path)

        _MODEL_CACHE["probability_model"] = probability_model
        _MODEL_CACHE["severity_model"] = severity_model
        _MODEL_CACHE["feature_columns"] = feature_columns

        return probability_model, severity_model, feature_columns
    except Exception as exc:
        logger.warning("Failed to load risk model artifacts: %s. Falling back to statistical estimate.", exc)
        return None, None, FEATURE_COLUMNS_DEFAULT


def estimate_weekly_risk(zone_id: str, db: Session) -> dict:
    """Predict coming-week disruption risk using trained models, with safe fallback."""
    probability_model, severity_model, feature_columns = _load_models_once()
    if probability_model is None or severity_model is None:
        logger.warning("Using mock risk fallback for zone %s because trained model artifacts are unavailable.", zone_id)
        return _statistical_fallback(zone_id=zone_id, db=db)

    now = datetime.now(timezone.utc)
    feature_values, data_weeks = _build_live_features(zone_id=zone_id, db=db, now=now)
    ordered_features = [float(feature_values.get(column, 0.0)) for column in feature_columns]
    x = np.array([ordered_features], dtype=np.float64)

    try:
        disruption_probability = float(probability_model.predict_proba(x)[0][1])
        model_confidence = float(np.max(probability_model.predict_proba(x)[0]))
        expected_severity = float(np.clip(severity_model.predict(x)[0], 0.0, 1.0))
    except Exception as exc:
        logger.warning("Risk model prediction failed: %s. Falling back to statistical estimate.", exc)
        logger.warning("Using mock risk fallback for zone %s because prediction failed.", zone_id)
        return _statistical_fallback(zone_id=zone_id, db=db)

    return {
        "expected_disruption_days": round(float(np.clip(disruption_probability, 0.0, 1.0) * 7.0), 3),
        "expected_severity": round(expected_severity, 3),
        "data_weeks": int(data_weeks),
        "used_fallback": False,
        "model_confidence": round(float(np.clip(model_confidence, 0.0, 1.0)), 3),
    }


def forecast_zone_risk_series(zone_id: str, db: Session, days: int = 7) -> list[dict]:
    """Return a 7-day zone risk series for the dashboard."""
    base = estimate_weekly_risk(zone_id=zone_id, db=db)
    signal_series = get_zone_intelligence_series(zone_id, days=days)
    series: list[dict] = []

    for day_offset, signal in enumerate(signal_series):
        signal_pressure = float(signal.get("signal_pressure", 0.0))
        holiday_boost = 0.12 if signal.get("holiday_active") else 0.0
        weekend_boost = 0.08 if datetime.fromisoformat(signal["forecast_date"]).weekday() >= 5 else 0.0
        daily_multiplier = 1.0 + (signal_pressure * 0.65) + holiday_boost + weekend_boost
        projected_disruption_days = min(7.0, float(base["expected_disruption_days"]) * daily_multiplier / 1.8)
        projected_severity = min(1.0, float(base["expected_severity"]) * (0.85 + signal_pressure * 0.35))

        series.append(
            {
                "zone_id": zone_id,
                "forecast_date": signal["forecast_date"],
                "day_offset": day_offset,
                "signal_pressure": round(signal_pressure, 3),
                "holiday_active": bool(signal.get("holiday_active")),
                "windspeed_10m_max_kph": float(signal.get("windspeed_10m_max_kph", 0.0)),
                "precipitation_sum_mm": float(signal.get("precipitation_sum_mm", 0.0)),
                "news_risk": float(signal.get("news_risk", 0.0)),
                "fire_risk": float(signal.get("fire_risk", 0.0)),
                "projected_disruption_days": round(projected_disruption_days, 3),
                "projected_severity": round(projected_severity, 3),
                "forecast_confidence": round(float(base.get("model_confidence", 0.0)) * (0.9 + (0.1 - signal_pressure * 0.03)), 3),
            }
        )

    return series
