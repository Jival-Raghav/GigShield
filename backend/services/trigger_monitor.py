"""Trigger monitoring service functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from mock_apis import (
    get_aqi,
    get_curfew_status,
    get_flood_alert,
    get_platform_status,
    get_rainfall,
    get_temperature,
)
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.policy import Policy
from models.worker import Worker
from services.claim_processing import evaluate_and_assign_claim, try_auto_pay_claim


def _severity(value: float) -> float:
    return float(round(max(0.0, min(value, 1.0)), 3))


async def check_all_triggers(zone_id: str, db: Session) -> list[dict]:
    """Check all configured mock trigger sources and return active disruptions."""
    disruptions: list[dict] = []

    rainfall = get_rainfall(zone_id)
    rainfall_mm = float(rainfall["rainfall_mm_per_hr"])
    if rainfall_mm > 50.0:
        sev = _severity(min(rainfall_mm / 100.0, 1.0))
        event_started_at = rainfall.get("event_started_at")
        event_ended_at = rainfall.get("event_ended_at")
        if event_started_at is None:
            duration_hours = float(rainfall.get("duration_hours", 1.0))
            event_ended_at = event_ended_at or datetime.now(timezone.utc)
            event_started_at = event_ended_at - timedelta(hours=max(duration_hours, 0.25))
        disruptions.append(
            {
                "zone_id": zone_id,
                "disruption_type": "rainfall",
                "severity": sev,
                "signal_source": rainfall.get("source", "IMD_MOCK"),
                "is_catastrophic": sev > 0.9,
                "started_at": event_started_at,
                "ended_at": event_ended_at,
            }
        )

    aqi_data = get_aqi(zone_id)
    aqi_value = int(aqi_data["aqi"])
    if aqi_value > 300:
        sev = _severity(min((aqi_value - 300) / 200.0, 1.0))
        disruptions.append(
            {
                "zone_id": zone_id,
                "disruption_type": "aqi",
                "severity": sev,
                "signal_source": aqi_data.get("source", "CPCB_MOCK"),
                "is_catastrophic": sev > 0.9,
            }
        )

    flood = get_flood_alert(zone_id)
    if flood["alert_active"]:
        base_severity = {
            "watch": 0.6,
            "warning": 0.85,
            "emergency": 0.95,
        }.get(flood["alert_level"], 0.85)
        sev = _severity(base_severity)
        disruptions.append(
            {
                "zone_id": zone_id,
                "disruption_type": "flood",
                "severity": sev,
                "signal_source": flood.get("source", "NDMA_MOCK"),
                "is_catastrophic": sev > 0.9,
            }
        )

    curfew = get_curfew_status(zone_id)
    if curfew["curfew_active"]:
        base_severity = 0.55 if curfew["curfew_level"] == "night" else 0.9
        sev = _severity(base_severity)
        disruptions.append(
            {
                "zone_id": zone_id,
                "disruption_type": "curfew",
                "severity": sev,
                "signal_source": curfew.get("source", "CIVIC_CURFEW_MOCK"),
                "is_catastrophic": sev > 0.9,
            }
        )

    platform = get_platform_status(zone_id)
    if platform["outage_active"]:
        sev = _severity(
            max(
                min(float(platform["api_error_rate"]) / 0.35, 1.0),
                min((100.0 - float(platform["uptime_percent"])) / 10.0, 1.0),
            )
        )
        disruptions.append(
            {
                "zone_id": zone_id,
                "disruption_type": "platform_outage",
                "severity": sev,
                "signal_source": platform.get("source", "PLATFORM_HEALTH_MOCK"),
                "is_catastrophic": sev > 0.9,
            }
        )

    weather = get_temperature(zone_id)
    temp = float(weather["temperature_celsius"])
    if temp >= 42.0 or temp <= 5.0:
        sev = _severity(min(abs(temp - 30.0) / 20.0, 1.0))
        disruptions.append(
            {
                "zone_id": zone_id,
                "disruption_type": "extreme_temperature",
                "severity": sev,
                "signal_source": weather.get("source", "IMD_MOCK"),
                "is_catastrophic": sev > 0.9,
            }
        )

    return disruptions


async def auto_initiate_claims(disruption: Disruption, db: Session) -> int:
    """Auto-create pending claims for workers in disruption zone with active policy."""
    if disruption.ended_at is None:
        return 0

    workers = db.query(Worker).filter(Worker.micro_zone_id == disruption.zone_id).all()
    initiated = 0

    for worker in workers:
        policy = (
            db.query(Policy)
            .filter(Policy.worker_id == worker.id, Policy.is_active.is_(True))
            .order_by(Policy.created_at.desc())
            .first()
        )
        if policy is None:
            continue

        existing_claim = (
            db.query(Claim)
            .filter(
                Claim.worker_id == worker.id,
                Claim.disruption_id == disruption.id,
            )
            .first()
        )
        if existing_claim is not None:
            continue

        claim = Claim(
            worker_id=worker.id,
            policy_id=policy.id,
            disruption_id=disruption.id,
            status=ClaimStatusEnum.validating,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        claim = evaluate_and_assign_claim(
            worker=worker,
            policy=policy,
            disruption=disruption,
            claim=claim,
            db=db,
        )
        db.add(claim)
        db.flush()
        try_auto_pay_claim(claim=claim, policy=policy, db=db, reference_prefix="AUTO-END")
        initiated += 1

    db.commit()
    return initiated
