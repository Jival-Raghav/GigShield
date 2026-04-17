"""Deterministic telemetry helpers for fraud signal evaluation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from statistics import mean

from sqlalchemy.orm import Session

from models.worker_income import WorkerDailyIncome
from services.zone_granularity import map_coordinates_to_zone, parent_zone_for, same_parent_zone

logger = logging.getLogger(__name__)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _parse_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _confidence_from_accuracy(accuracy_meters: float | None) -> float:
    if accuracy_meters is None:
        return 0.88
    return round(_clamp(1.0 - (float(accuracy_meters) / 250.0), 0.55, 0.99), 3)


def get_gps_signal(
    worker_id: str,
    claimed_zone_id: str,
    home_zone_id: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_meters: float | None = None,
) -> dict:
    """Return a deterministic GPS snapshot from browser coordinates."""
    logger.warning("Using mock GPS signal for worker %s in zone %s.", worker_id, claimed_zone_id)
    mapped_zone = map_coordinates_to_zone(latitude=latitude, longitude=longitude)
    fallback_parent_zone = home_zone_id or claimed_zone_id
    gps_parent_zone = (mapped_zone or {}).get("parent_zone_id", fallback_parent_zone)
    gps_fine_zone = (mapped_zone or {}).get("fine_zone_id")
    gps_confidence = _confidence_from_accuracy(accuracy_meters)
    gps_mismatch = not same_parent_zone(gps_parent_zone, claimed_zone_id)

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "gps_zone": gps_parent_zone,
        "gps_micro_zone": gps_fine_zone,
        "gps_confidence": gps_confidence,
        "gps_mismatch": gps_mismatch,
        "gps_micro_zone_mismatch": bool(gps_fine_zone) and parent_zone_for(str(gps_fine_zone)) != parent_zone_for(claimed_zone_id),
        "gps_lookup_status": "matched" if mapped_zone is not None else "fallback",
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_meters": accuracy_meters,
        "source": "GPS_DETERMINISTIC",
        "timestamp": datetime.now(timezone.utc),
    }


def get_cell_tower_signal(worker_id: str, claimed_zone_id: str, gps_zone: str | None = None) -> dict:
    """Return deterministic cell-tower zone estimation."""
    logger.warning("Using mock cell tower signal for worker %s in zone %s.", worker_id, claimed_zone_id)
    if gps_zone is not None and gps_zone != claimed_zone_id:
        cell_zone = f"{claimed_zone_id}-adjacent"
    else:
        cell_zone = claimed_zone_id

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "cell_tower_zone": cell_zone,
        "cell_tower_mismatch": cell_zone != claimed_zone_id,
        "source": "CELL_TOWER_RULE_BASED",
        "timestamp": datetime.now(timezone.utc),
    }


def _lookup_zone_from_ip(ip_address: str | None, claimed_zone_id: str) -> tuple[str, str]:
    if not ip_address:
        return claimed_zone_id, "fallback"

    normalized_ip = ip_address.strip().lower()
    prefix_zone_map = {
        "127.0.0.1": "BLR_KORAMANGALA_CENTRAL",
        "10.": "BLR_KORAMANGALA_CENTRAL",
        "172.16.": "PUN_KOTHRUD_CENTRAL",
        "192.168.": "HYD_GACHIBOWLI_CENTRAL",
        "203.0.113.": "BLR_KORAMANGALA_SE",
        "198.51.100.": "PUN_KOTHRUD_W",
        "192.0.2.": "HYD_GACHIBOWLI_E",
    }

    for prefix, zone_id in prefix_zone_map.items():
        if normalized_ip.startswith(prefix):
            return zone_id, "mapped"

    return claimed_zone_id, "fallback"


def get_ip_geolocation_signal(worker_id: str, claimed_zone_id: str, ip_address: str | None = None) -> dict:
    """Return a deterministic IP based zone estimate."""
    logger.warning("Using mock IP geolocation signal for worker %s in zone %s.", worker_id, claimed_zone_id)
    ip_zone_raw, lookup_status = _lookup_zone_from_ip(ip_address=ip_address, claimed_zone_id=claimed_zone_id)
    ip_zone_parent = parent_zone_for(ip_zone_raw)

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "ip_zone": ip_zone_parent,
        "ip_micro_zone": ip_zone_raw if ip_zone_raw != ip_zone_parent else None,
        "ip_mismatch": not same_parent_zone(ip_zone_parent, claimed_zone_id),
        "ip_lookup_status": lookup_status,
        "ip_address": ip_address,
        "source": "IP_GEO_DETERMINISTIC",
        "timestamp": datetime.now(timezone.utc),
    }


def get_motion_signal(worker_id: str, claimed_zone_id: str, online_hours: float | None = None) -> dict:
    """Return a deterministic motion signal derived from activity duration."""
    logger.warning("Using mock motion signal for worker %s in zone %s.", worker_id, claimed_zone_id)
    effective_online_hours = 4.0 if online_hours is None else max(float(online_hours), 0.0)
    is_stationary = effective_online_hours < 2.0

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "is_stationary": is_stationary,
        "online_hours": round(effective_online_hours, 2),
        "source": "ACCELEROMETER_RULE_BASED",
        "timestamp": datetime.now(timezone.utc),
    }


def _derive_activity_row(row: object, baseline_income: float) -> tuple[int, int, float]:
    if isinstance(row, dict):
        assigned = int(row.get("orders_assigned") or 0)
        accepted = int(row.get("orders_accepted") or 0)
        online_minutes = float(row.get("online_minutes") or 0.0)
        if assigned > 0 and accepted > 0:
            return assigned, accepted, online_minutes

    income = float(getattr(row, "daily_income", 0.0) or 0.0)
    baseline_income = max(baseline_income, 1.0)
    assigned = max(1, round(income / 80.0))
    acceptance_rate = _clamp(income / baseline_income, 0.05, 0.98)
    accepted = max(0, round(assigned * acceptance_rate))
    online_hours = _clamp((income / baseline_income) * 8.0, 0.5, 12.0)
    return assigned, accepted, online_hours * 60.0


def _summarize_activity(rows: list[object], baseline_income: float) -> dict:
    if not rows:
        return {
            "orders_assigned": 0,
            "orders_accepted": 0,
            "online_minutes": 0.0,
            "acceptance_rate": 0.0,
            "online_hours": 0.0,
        }

    assigned_total = 0
    accepted_total = 0
    online_minutes_total = 0.0
    for row in rows:
        assigned, accepted, online_minutes = _derive_activity_row(row, baseline_income=baseline_income)
        assigned_total += assigned
        accepted_total += min(accepted, assigned)
        online_minutes_total += online_minutes

    acceptance_rate = accepted_total / assigned_total if assigned_total > 0 else 0.0
    online_hours = online_minutes_total / 60.0
    return {
        "orders_assigned": assigned_total,
        "orders_accepted": accepted_total,
        "online_minutes": round(online_minutes_total, 2),
        "acceptance_rate": round(acceptance_rate, 3),
        "online_hours": round(online_hours, 2),
    }


def _income_value(row: object) -> float:
    if isinstance(row, dict):
        return float(row.get("daily_income", 0.0) or 0.0)
    return float(getattr(row, "daily_income", 0.0) or 0.0)


def get_order_activity_signal(
    worker_id: str,
    claimed_zone_id: str,
    disruption_severity: float = 0.0,
    db: Session | None = None,
    claim_timestamp: datetime | None = None,
    activity_rows: list[dict] | None = None,
) -> dict:
    """Return deterministic order activity metrics from stored history or provided rows."""
    claim_time = claim_timestamp if isinstance(claim_timestamp, datetime) else datetime.now(timezone.utc)
    severity = _clamp(float(disruption_severity), 0.0, 1.0)

    before_rows: list[object] = []
    during_rows: list[object] = []
    baseline_income = 0.0
    activity_source = "fallback_rules"
    logger.warning("Using mock order activity signal for worker %s in zone %s.", worker_id, claimed_zone_id)

    if activity_rows is not None:
        activity_source = "provided_rows"
        cutoff = claim_time.timestamp() - (6 * 3600)
        for row in activity_rows:
            row_timestamp = row.get("timestamp") if isinstance(row, dict) else None
            if isinstance(row_timestamp, datetime) and row_timestamp.timestamp() >= cutoff:
                during_rows.append(row)
            else:
                before_rows.append(row)
        income_values = [float(row.get("daily_income", 0.0)) for row in activity_rows if isinstance(row, dict)]
        baseline_income = mean(income_values) if income_values else 0.0
    elif db is not None:
        parsed_worker_id = _parse_uuid(worker_id)
        if parsed_worker_id is not None:
            worker_rows = (
                db.query(WorkerDailyIncome)
                .filter(WorkerDailyIncome.worker_id == parsed_worker_id)
                .order_by(WorkerDailyIncome.date.asc())
                .all()
            )
            claim_date = claim_time.date()
            before_rows = [row for row in worker_rows if row.date < claim_date][-7:]
            during_rows = [row for row in worker_rows if row.date == claim_date]
            if not during_rows and worker_rows:
                during_rows = [worker_rows[-1]]
            before_income_values = [float(row.clean_income if row.clean_income is not None else row.daily_income) for row in before_rows]
            baseline_income = mean(before_income_values) if before_income_values else 0.0
            activity_source = "worker_daily_income"

    if baseline_income <= 0 and before_rows:
        before_income_values = [_income_value(row) for row in before_rows]
        baseline_income = mean(before_income_values) if before_income_values else 0.0

    before_summary = _summarize_activity(before_rows, baseline_income=max(baseline_income, 1.0))
    during_summary = _summarize_activity(during_rows, baseline_income=max(baseline_income, 1.0))

    if not before_rows and not during_rows:
        before_acceptance = 0.72
        during_acceptance = _clamp(0.72 - (severity * 0.18), 0.05, 0.95)
        before_online_hours = 7.5
        during_online_hours = _clamp(7.5 - (severity * 2.75), 0.5, 12.0)
    else:
        before_acceptance = before_summary["acceptance_rate"] or 0.72
        during_acceptance = during_summary["acceptance_rate"] or _clamp(before_acceptance - (severity * 0.15), 0.05, 0.95)
        before_online_hours = before_summary["online_hours"] or 7.5
        during_online_hours = during_summary["online_hours"] or _clamp(before_online_hours - (severity * 2.0), 0.5, 12.0)

    acceptance_drop = max(0.0, round(before_acceptance - during_acceptance, 3))
    online_hours_during = round(during_online_hours, 2)

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "before_acceptance": round(before_acceptance, 3),
        "during_acceptance": round(during_acceptance, 3),
        "acceptance_drop": acceptance_drop,
        "before_online_hours": round(before_online_hours, 2),
        "during_online_hours": online_hours_during,
        "acceptance_rate_during": round(during_acceptance, 3),
        "online_hours_during": online_hours_during,
        "orders_assigned_before": int(before_summary["orders_assigned"]),
        "orders_accepted_before": int(before_summary["orders_accepted"]),
        "orders_assigned_during": int(during_summary["orders_assigned"]),
        "orders_accepted_during": int(during_summary["orders_accepted"]),
        "activity_source": activity_source,
        "source": "ORDER_ACTIVITY_DETERMINISTIC",
        "timestamp": claim_time,
    }
