"""Claim timeline and what-if simulation helpers."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.orm import Session

from models.claim import Claim
from models.payout import Payout
from models.worker import Worker
from models.worker_location_trace import WorkerLocationTrace
from services import fraud_ai, fraud_detection, payout_engine
from services.intelligence_signals import get_zone_intelligence_snapshot


def _serialize_dt(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _latest_trace(worker_id, claim_time: datetime, db: Session) -> WorkerLocationTrace | None:
    return (
        db.query(WorkerLocationTrace)
        .filter(WorkerLocationTrace.worker_id == worker_id, WorkerLocationTrace.created_at <= claim_time)
        .order_by(WorkerLocationTrace.created_at.desc())
        .first()
    )


def build_claim_timeline(claim_id: str, db: Session) -> dict:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        return {"claim_id": claim_id, "timeline": []}

    worker = db.query(Worker).filter(Worker.id == claim.worker_id).first()
    if worker is None:
        return {"claim_id": claim_id, "timeline": []}

    claim_time = claim.created_at if isinstance(claim.created_at, datetime) else datetime.now(timezone.utc)
    trace = _latest_trace(worker.id, claim_time, db)
    reconstructed = fraud_detection.build_claim_metadata(
        worker=worker,
        claimed_zone_id=worker.micro_zone_id,
        db=db,
        latitude=trace.latitude if trace else None,
        longitude=trace.longitude if trace else None,
        accuracy_meters=trace.accuracy_meters if trace else None,
        claim_timestamp=claim_time,
    )
    zone_intelligence = get_zone_intelligence_snapshot(worker.micro_zone_id, forecast_date=claim_time.date())
    payout = db.query(Payout).filter(Payout.claim_id == claim.id).first()

    events = [
        {
            "timestamp": _serialize_dt(claim.created_at),
            "category": "claim",
            "title": "Claim created",
            "details": f"Claim entered validation for zone {worker.micro_zone_id}",
        },
    ]

    if trace is not None:
        events.append(
            {
                "timestamp": _serialize_dt(trace.created_at),
                "category": "location",
                "title": "Latest worker location trace",
                "details": f"GPS mapped to {trace.mapped_parent_zone_id or 'unknown'} / {trace.mapped_fine_zone_id or 'unknown'}",
            }
        )

    events.extend(
        [
            {
                "timestamp": _serialize_dt(reconstructed["claim_timestamp"]),
                "category": "signals",
                "title": "Zone signal snapshot",
                "details": (
                    f"GPS zone {reconstructed['gps_zone']}, IP zone {reconstructed['ip_zone']}, "
                    f"stationary={reconstructed['is_stationary']}"
                ),
            },
            {
                "timestamp": _serialize_dt(claim.created_at),
                "category": "environment",
                "title": "Weather / AQI / event pressure",
                "details": (
                    f"Weather pressure={zone_intelligence['signal_pressure']:.2f}, holiday={zone_intelligence['holiday_active']}, "
                    f"wind={zone_intelligence['windspeed_10m_max_kph']} kph, rain={zone_intelligence['precipitation_sum_mm']} mm"
                ),
            },
            {
                "timestamp": _serialize_dt(claim.updated_at),
                "category": "fraud",
                "title": "Fraud evaluation",
                "details": f"Score {float((1.0 - float(claim.signal_confidence or 0.0)) * 100.0):.1f}/100, band={('high' if (1.0 - float(claim.signal_confidence or 0.0)) * 100 >= 75 else 'medium' if (1.0 - float(claim.signal_confidence or 0.0)) * 100 >= 55 else 'low')}",
            },
        ]
    )

    if payout is not None:
        events.append(
            {
                "timestamp": _serialize_dt(payout.completed_at or payout.initiated_at),
                "category": "payout",
                "title": f"Payout {payout.payment_status.value}",
                "details": f"{payout.amount:.2f} via {payout.payment_method.value}",
            }
        )

    events.append(
        {
            "timestamp": _serialize_dt(claim.updated_at),
            "category": "decision",
            "title": "Current claim status",
            "details": f"{claim.status.value} | audit_required={claim.audit_required}",
        }
    )

    return {
        "claim_id": str(claim.id),
        "worker_id": str(worker.id),
        "zone_id": worker.micro_zone_id,
        "fraud_score": round((1.0 - float(claim.signal_confidence or 0.0)) * 100.0, 2),
        "fraud_band": "high" if (1.0 - float(claim.signal_confidence or 0.0)) * 100 >= 75 else "medium" if (1.0 - float(claim.signal_confidence or 0.0)) * 100 >= 55 else "low",
        "timeline": events,
    }


def simulate_claim_scenario(claim_id: str, overrides: dict, db: Session) -> dict:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        return {"claim_id": claim_id, "error": "Claim not found"}

    worker = db.query(Worker).filter(Worker.id == claim.worker_id).first()
    if worker is None:
        return {"claim_id": claim_id, "error": "Worker not found"}

    disruption = claim.disruption
    policy = claim.policy
    base_timeline = build_claim_timeline(claim_id, db)

    trace = _latest_trace(worker.id, claim.created_at, db) if isinstance(claim.created_at, datetime) else None
    metadata = fraud_detection.build_claim_metadata(
        worker=worker,
        claimed_zone_id=disruption.zone_id,
        db=db,
        latitude=trace.latitude if trace else None,
        longitude=trace.longitude if trace else None,
        accuracy_meters=trace.accuracy_meters if trace else None,
        claim_timestamp=claim.created_at,
    )
    metadata = deepcopy(metadata)
    zone_context = deepcopy(metadata.get("disruption_context", {}))

    if overrides.get("worker_movement") == "stationary":
        metadata["is_stationary"] = True
    elif overrides.get("worker_movement") == "mobile":
        metadata["is_stationary"] = False

    if overrides.get("gps_zone"):
        metadata["gps_zone"] = overrides["gps_zone"]
    if overrides.get("ip_zone"):
        metadata["ip_zone"] = overrides["ip_zone"]
    if overrides.get("curfew_level"):
        zone_context["curfew_level"] = overrides["curfew_level"]
        zone_context["curfew_active"] = overrides["curfew_level"] != "none"
        zone_context["severity_index"] = max(float(zone_context.get("severity_index", 0.0)), 0.55 if overrides["curfew_level"] == "night" else 0.9)
    if overrides.get("rainfall_mm") is not None:
        rainfall = float(overrides["rainfall_mm"])
        zone_context["rainfall_mm_per_hr"] = rainfall
        zone_context["severity_index"] = max(float(zone_context.get("severity_index", 0.0)), min(rainfall / 100.0, 1.0))
    if overrides.get("aqi") is not None:
        aqi = float(overrides["aqi"])
        zone_context["aqi"] = aqi
        zone_context["severity_index"] = max(float(zone_context.get("severity_index", 0.0)), min(max(aqi - 300.0, 0.0) / 200.0, 1.0))
    if overrides.get("wind_speed_kph") is not None:
        zone_context["windspeed_10m_max_kph"] = float(overrides["wind_speed_kph"])
        zone_context["severity_index"] = max(float(zone_context.get("severity_index", 0.0)), min(float(overrides["wind_speed_kph"]) / 70.0, 1.0))
    if overrides.get("external_pressure") is not None:
        zone_context["severity_index"] = max(float(zone_context.get("severity_index", 0.0)), float(overrides["external_pressure"]))

    metadata["disruption_context"] = zone_context

    synthetic_severity = float(overrides.get("disruption_severity", disruption.severity))
    if zone_context.get("severity_index") is not None:
        synthetic_severity = max(synthetic_severity, float(zone_context["severity_index"]))

    synthetic_disruption = SimpleNamespace(
        zone_id=disruption.zone_id,
        disruption_type=disruption.disruption_type,
        severity=synthetic_severity,
        started_at=disruption.started_at,
        ended_at=disruption.ended_at,
        is_catastrophic=bool(synthetic_severity > 0.9),
    )

    spoof_result = fraud_detection.run_spoofing_check(
        worker=worker,
        claimed_zone_id=disruption.zone_id,
        claim_metadata=metadata,
        db=db,
    )
    baf_score = payout_engine.compute_baf(worker=worker, claim=claim, disruption=synthetic_disruption, db=db)
    payout_result = payout_engine.calculate_payout(
        worker=worker,
        claim=claim,
        policy=policy,
        disruption=synthetic_disruption,
        baf_score=baf_score,
    )
    fraud = fraud_ai.assess_claim_fraud(
        db=db,
        worker=worker,
        disruption=synthetic_disruption,
        claim_metadata=metadata,
        spoof_result=spoof_result,
        baf_score=baf_score,
    )

    base_fraud_score = float(base_timeline.get("fraud_score", 0.0))
    base_payout = float(claim.payout_amount or 0.0)
    simulated_payout = float(payout_result.get("adjusted_payout", 0.0))

    return {
        "claim_id": str(claim.id),
        "base": {
            "fraud_score": round(base_fraud_score, 2),
            "fraud_band": base_timeline.get("fraud_band", "low"),
            "payout_amount": round(base_payout, 2),
        },
        "scenario": {
            "fraud_score": round(float(fraud.fraud_score), 2),
            "fraud_band": fraud.fraud_band,
            "payout_amount": round(simulated_payout, 2),
            "payout_income_lost": round(float(payout_result.get("income_lost", 0.0)), 2),
            "eligible_hours": round(float(payout_result.get("eligible_hours", 0.0)), 2),
            "severity_smoothed": round(float(payout_result.get("severity_smoothed", 0.0)), 3),
            "audit_required": bool(fraud.fraud_score >= 55.0 or spoof_result.get("audit_required", False)),
            "top_reasons": fraud.top_reasons,
            "explanation": fraud.explanation,
        },
        "delta": {
            "fraud_score": round(float(fraud.fraud_score) - base_fraud_score, 2),
            "payout_amount": round(simulated_payout - base_payout, 2),
        },
    }
