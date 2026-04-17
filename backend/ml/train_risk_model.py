"""Train Raah Saathi weekly risk models using disruption history."""

from __future__ import annotations

import logging
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random

import joblib
import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import classification_report, mean_absolute_error
from sklearn.model_selection import KFold, StratifiedKFold
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from mock_apis import get_aqi, get_rainfall
from models.disruption import Disruption
from models.worker import Worker

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
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

SYNTHETIC_ZONE_CONFIG = {
    2: {"sev_mean": 0.70, "recent_mean": 7.0, "month_last_year_mean": 3.0},
    1: {"sev_mean": 0.50, "recent_mean": 3.0, "month_last_year_mean": 1.2},
    0: {"sev_mean": 0.30, "recent_mean": 1.0, "month_last_year_mean": 0.4},
}


def _selected_family() -> str:
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
    """Approximate disruption pressure from mock weather and AQI signals."""
    logger.warning("Using mock weather and AQI data while training risk model for zone %s.", zone_id)
    rainfall = get_rainfall(zone_id)
    aqi = get_aqi(zone_id)

    rainfall_mm = float(rainfall.get("rainfall_mm_per_hr", 0.0))
    aqi_value = float(aqi.get("aqi", 0.0))

    rainfall_score = min(rainfall_mm / 100.0, 1.0)
    aqi_score = min(max(aqi_value - 100.0, 0.0) / 400.0, 1.0)
    return float(np.clip(0.55 * rainfall_score + 0.45 * aqi_score, 0.0, 1.0))


def _collect_zone_platform_index(db: Session) -> dict[str, float]:
    workers = db.query(Worker).all()
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for worker in workers:
        grouped[worker.micro_zone_id][worker.platform.value.lower()] += 1

    zone_platform_index: dict[str, float] = {}
    for zone_id, counts in grouped.items():
        platform, _ = counts.most_common(1)[0]
        zone_platform_index[zone_id] = PLATFORM_VOLATILITY.get(platform, 1.1)
    return zone_platform_index


def _month_bounds_for_last_year(reference_week: datetime) -> tuple[datetime, datetime]:
    month_start = reference_week.replace(day=1)
    last_year_start = month_start.replace(year=month_start.year - 1)
    if last_year_start.month == 12:
        next_month = last_year_start.replace(year=last_year_start.year + 1, month=1)
    else:
        next_month = last_year_start.replace(month=last_year_start.month + 1)
    return last_year_start, next_month


def _build_rows_from_history(db: Session) -> list[dict]:
    disruptions = db.query(Disruption).order_by(Disruption.started_at.asc()).all()
    if not disruptions:
        return []

    zones_from_disruptions = {row.zone_id for row in disruptions}
    zones_from_workers = {worker.micro_zone_id for worker in db.query(Worker).all()}
    zones = sorted(zones_from_disruptions | zones_from_workers)
    if not zones:
        return []

    by_zone_week: dict[tuple[str, datetime], list[Disruption]] = defaultdict(list)
    by_zone: dict[str, list[Disruption]] = defaultdict(list)
    for row in disruptions:
        wk = _week_start(row.started_at)
        by_zone_week[(row.zone_id, wk)].append(row)
        by_zone[row.zone_id].append(row)

    min_week = _week_start(disruptions[0].started_at)
    max_week = _week_start(disruptions[-1].started_at)

    all_weeks: list[datetime] = []
    cursor = min_week
    while cursor <= max_week:
        all_weeks.append(cursor)
        cursor = cursor + timedelta(weeks=1)

    zone_platform_index = _collect_zone_platform_index(db)

    rows: list[dict] = []
    for zone_id in zones:
        zone_rows = by_zone.get(zone_id, [])

        for week in all_weeks:
            week_of_year = int(week.strftime("%V"))
            month = int(week.month)
            zone_bucket = _zone_risk_bucket(zone_id)

            lookback_start = week - timedelta(weeks=4)
            lookback_rows = [
                row for row in zone_rows if lookback_start <= _week_start(row.started_at) < week
            ]
            disruptions_last_4_weeks = len(lookback_rows)

            if lookback_rows:
                avg_severity_last_4_weeks = float(
                    np.mean([float(row.severity) for row in lookback_rows])
                )
            else:
                # Use mock weather + AQI when no recent disruption history exists.
                avg_severity_last_4_weeks = _signal_pressure(zone_id)

            month_last_year_start, month_last_year_end = _month_bounds_for_last_year(week)
            disruptions_same_month_last_year = sum(
                1
                for row in zone_rows
                if month_last_year_start <= row.started_at.astimezone(timezone.utc) < month_last_year_end
            )

            current_week_rows = by_zone_week.get((zone_id, week), [])
            disruption_probability_target = 1 if current_week_rows else 0
            expected_severity_target = (
                float(np.mean([float(row.severity) for row in current_week_rows])) if current_week_rows else 0.0
            )

            rows.append(
                {
                    "week_of_year": week_of_year,
                    "month": month,
                    "zone_risk_bucket": zone_bucket,
                    "disruptions_last_4_weeks": disruptions_last_4_weeks,
                    "avg_severity_last_4_weeks": round(avg_severity_last_4_weeks, 4),
                    "disruptions_same_month_last_year": disruptions_same_month_last_year,
                    "platform_volatility_index": float(zone_platform_index.get(zone_id, 1.1)),
                    "disruption_probability": disruption_probability_target,
                    "expected_severity": round(expected_severity_target, 4),
                }
            )

    return rows


def _augment_with_synthetic(rows: list[dict], count: int = 500) -> list[dict]:
    rng = Random(42)
    np_rng = np.random.default_rng(42)
    augmented = list(rows)

    print("WARNING: Training on augmented data — replace with real data before production")

    synthetic_targets = [1] * (count // 2) + [0] * (count - (count // 2))
    rng.shuffle(synthetic_targets)

    for disruption_probability in synthetic_targets:
        zone_bucket = rng.choices([2, 1, 0], weights=[0.3, 0.5, 0.2], k=1)[0]
        cfg = SYNTHETIC_ZONE_CONFIG[zone_bucket]

        week_of_year = rng.randint(1, 52)
        month = rng.randint(1, 12)

        disruptions_last_4_weeks = float(max(np_rng.poisson(cfg["recent_mean"]), 0))
        avg_severity_last_4_weeks = float(np.clip(np_rng.normal(cfg["sev_mean"], 0.12), 0.0, 1.0))
        disruptions_same_month_last_year = float(max(np_rng.poisson(cfg["month_last_year_mean"]), 0))
        platform_volatility_index = float(np.clip(np_rng.normal(1.1, 0.08), 0.85, 1.25))

        # Gaussian noise across numeric features.
        week_of_year = int(np.clip(round(week_of_year + np_rng.normal(0, 1.2)), 1, 52))
        month = int(np.clip(round(month + np_rng.normal(0, 0.6)), 1, 12))
        disruptions_last_4_weeks = float(max(disruptions_last_4_weeks + np_rng.normal(0, 1.0), 0.0))
        avg_severity_last_4_weeks = float(np.clip(avg_severity_last_4_weeks + np_rng.normal(0, 0.06), 0.0, 1.0))
        disruptions_same_month_last_year = float(max(disruptions_same_month_last_year + np_rng.normal(0, 0.8), 0.0))
        platform_volatility_index = float(np.clip(platform_volatility_index + np_rng.normal(0, 0.03), 0.8, 1.3))

        if disruption_probability == 1:
            expected_severity = float(np.clip(np_rng.normal(cfg["sev_mean"], 0.1), 0.0, 1.0))
            disruptions_last_4_weeks = float(max(disruptions_last_4_weeks + np_rng.normal(2.5, 0.8), 0.0))
        else:
            expected_severity = 0.0
            disruptions_last_4_weeks = float(max(disruptions_last_4_weeks + np_rng.normal(-0.8, 0.6), 0.0))

        augmented.append(
            {
                "week_of_year": week_of_year,
                "month": month,
                "zone_risk_bucket": zone_bucket,
                "disruptions_last_4_weeks": round(disruptions_last_4_weeks, 4),
                "avg_severity_last_4_weeks": round(avg_severity_last_4_weeks, 4),
                "disruptions_same_month_last_year": int(round(disruptions_same_month_last_year)),
                "platform_volatility_index": round(platform_volatility_index, 4),
                "disruption_probability": disruption_probability,
                "expected_severity": round(expected_severity, 4),
            }
        )

    return augmented


def _to_matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.array([[float(row[col]) for col in FEATURE_COLUMNS] for row in rows], dtype=np.float64)
    y_prob = np.array([int(row["disruption_probability"]) for row in rows], dtype=np.int32)
    y_sev = np.array([float(row["expected_severity"]) for row in rows], dtype=np.float64)
    return x, y_prob, y_sev


def _build_probability_model(family: str):
    if family == "xgboost":
        try:
            from xgboost import XGBClassifier

            return XGBClassifier(
                n_estimators=120,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                random_state=42,
                n_jobs=4,
            )
        except Exception:
            pass
    if family == "lightgbm":
        try:
            from lightgbm import LGBMClassifier

            return LGBMClassifier(
                n_estimators=160,
                learning_rate=0.06,
                num_leaves=31,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
            )
        except Exception:
            pass
    return GradientBoostingClassifier(random_state=42)


def _build_severity_model(family: str):
    if family == "xgboost":
        try:
            from xgboost import XGBRegressor

            return XGBRegressor(
                n_estimators=120,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                n_jobs=4,
            )
        except Exception:
            pass
    if family == "lightgbm":
        try:
            from lightgbm import LGBMRegressor

            return LGBMRegressor(
                n_estimators=160,
                learning_rate=0.06,
                num_leaves=31,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
            )
        except Exception:
            pass
    return GradientBoostingRegressor(random_state=42)


def _print_class_counts(label: str, y: np.ndarray) -> None:
    counts = Counter(int(v) for v in y.tolist())
    print(f"{label}: class_0={counts.get(0, 0)}, class_1={counts.get(1, 0)}")


def _build_smote(y: np.ndarray) -> SMOTE:
    counts = Counter(int(v) for v in y.tolist())
    minority = min(counts.values())
    if minority < 2:
        raise RuntimeError("Not enough minority samples for SMOTE. Add more training data.")
    return SMOTE(random_state=42, k_neighbors=min(5, minority - 1))


def _train_and_save(rows: list[dict]) -> None:
    x, y_prob, y_sev = _to_matrix(rows)
    family = _selected_family()

    if len(np.unique(y_prob)) < 2:
        raise RuntimeError("Classifier requires both classes. Add more disruption data before training.")

    _print_class_counts("Before SMOTE", y_prob)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_cv = np.zeros_like(y_prob)

    for train_idx, test_idx in skf.split(x, y_prob):
        x_train_fold, y_train_fold = x[train_idx], y_prob[train_idx]
        x_test_fold = x[test_idx]

        smote_fold = _build_smote(y_train_fold)
        x_train_bal, y_train_bal = smote_fold.fit_resample(x_train_fold, y_train_fold)

        clf_fold = _build_probability_model(family)
        clf_fold.fit(x_train_bal, y_train_bal)
        y_pred_cv[test_idx] = clf_fold.predict(x_test_fold)

    print("\n=== Disruption Probability Model (Classifier) ===")
    print(classification_report(y_prob, y_pred_cv, zero_division=0))

    smote_full = _build_smote(y_prob)
    x_balanced, y_balanced = smote_full.fit_resample(x, y_prob)
    _print_class_counts("After SMOTE", y_balanced)

    prob_model = _build_probability_model(family)
    prob_model.fit(x_balanced, y_balanced)

    disrupted_idx = np.where(y_prob == 1)[0]
    if disrupted_idx.size < 8:
        raise RuntimeError("Not enough disrupted-week samples to train severity model")

    x_sev = x[disrupted_idx]
    y_sev_only = y_sev[disrupted_idx]

    n_splits = min(5, len(y_sev_only))
    if n_splits < 2:
        raise RuntimeError("Not enough disrupted-week samples for severity cross-validation")

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_mae: list[float] = []
    for train_idx, test_idx in kf.split(x_sev):
        x_train_sev, x_test_sev = x_sev[train_idx], x_sev[test_idx]
        y_train_sev, y_test_sev = y_sev_only[train_idx], y_sev_only[test_idx]

        sev_fold = _build_severity_model(family)
        sev_fold.fit(x_train_sev, y_train_sev)
        y_pred_sev = sev_fold.predict(x_test_sev)
        fold_mae.append(mean_absolute_error(y_test_sev, y_pred_sev))

    mae = float(np.mean(fold_mae))

    sev_model = _build_severity_model(family)
    sev_model.fit(x_sev, y_sev_only)

    print("\n=== Severity Model (Regressor) ===")
    print(f"MAE: {mae:.4f}")

    ml_dir = Path(__file__).resolve().parent
    if family == "gradient_boosting":
        joblib.dump(prob_model, ml_dir / "risk_probability_model.joblib")
        joblib.dump(sev_model, ml_dir / "risk_severity_model.joblib")
    else:
        joblib.dump(prob_model, ml_dir / f"risk_probability_model_{family}.joblib")
        joblib.dump(sev_model, ml_dir / f"risk_severity_model_{family}.joblib")

    with (ml_dir / "feature_columns.json").open("w", encoding="utf-8") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)

    print("\nSaved model artifacts:")
    print(f"- {ml_dir / 'risk_probability_model.joblib'}")
    print(f"- {ml_dir / 'risk_severity_model.joblib'}")
    print(f"- {ml_dir / 'feature_columns.json'}")


def main() -> None:
    db = SessionLocal()
    try:
        rows = _build_rows_from_history(db)
        if not rows:
            raise RuntimeError("No disruption history found. Seed data first using python -m db.seed_data")

        print(f"Collected training rows from history: {len(rows)}")
        if len(rows) < 30:
            rows = _augment_with_synthetic(rows, count=500)
            print(f"Training rows after augmentation: {len(rows)}")

        _train_and_save(rows)
    finally:
        db.close()


if __name__ == "__main__":
    main()
