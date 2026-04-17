"""Fraud intelligence scoring and explanation utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.worker_location_trace import WorkerLocationTrace
from models.worker import Worker
from services.zone_granularity import parent_zone_for


@dataclass
class FraudAssessment:
    fraud_score: float
    fraud_band: str
    component_scores: dict[str, float]
    top_reasons: list[str]
    explanation: str
    explanation_confidence: float
    explanation_source: str


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(value, high))


def _risk_band(score: float) -> str:
    if score >= 75.0:
        return "high"
    if score >= 55.0:
        return "medium"
    return "low"


def _cross_signal_conflict_score(claim_metadata: dict, spoof_result: dict) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    gps_zone = str(claim_metadata.get("gps_zone", ""))
    ip_zone = str(claim_metadata.get("ip_zone", ""))
    cell_zone = str(claim_metadata.get("cell_tower_zone", ""))
    zone_id = str(claim_metadata.get("zone_id", ""))

    if gps_zone and ip_zone and gps_zone != ip_zone:
        score += 30.0
        reasons.append("GPS and IP geolocation disagree")

    if bool(claim_metadata.get("is_stationary", False)) and float(claim_metadata.get("online_hours_during", 0.0)) > 6.0:
        score += 25.0
        reasons.append("Device appears stationary despite high online activity")

    if cell_zone and zone_id and cell_zone != zone_id:
        score += 20.0
        reasons.append("Cell tower zone does not match claimed zone")

    failed_signals = spoof_result.get("failed_signals", [])
    if len(failed_signals) >= 3:
        score += 20.0
        reasons.append("Multiple spoofing checks failed")

    return _clamp(score), reasons


def _historical_fraud_likelihood(db: Session, worker: Worker, disruption: Disruption, claim_metadata: dict, baf_score: float) -> tuple[float, list[str]]:
    reasons: list[str] = []
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=60)

    prior_claims = (
        db.query(Claim)
        .join(Disruption, Disruption.id == Claim.disruption_id)
        .filter(
            Claim.created_at >= start_time,
            Disruption.zone_id == disruption.zone_id,
            Claim.worker_id != worker.id,
        )
        .all()
    )

    if not prior_claims:
        return 0.0, reasons

    suspicious = [c for c in prior_claims if c.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected} or c.audit_required]
    suspicious_ratio = len(suspicious) / max(len(prior_claims), 1)
    zone_risk = _clamp(suspicious_ratio * 100.0)

    worker_recent = (
        db.query(Claim)
        .filter(Claim.worker_id == worker.id)
        .order_by(Claim.created_at.desc())
        .limit(8)
        .all()
    )
    worker_history_flags = len([c for c in worker_recent if c.audit_required or c.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected}])
    worker_history_score = _clamp(worker_history_flags * 12.5)

    acceptance_drop = float(claim_metadata.get("acceptance_drop", 0.0))
    pattern_score = 0.0
    if acceptance_drop > 0.35 and baf_score < 0.45:
        pattern_score = 25.0
        reasons.append("Current behavior resembles prior suspicious patterns")

    score = _clamp((0.45 * zone_risk) + (0.35 * worker_history_score) + (0.20 * pattern_score))
    if score >= 40.0:
        reasons.append(f"Historical risk elevated in zone {disruption.zone_id}")

    return score, reasons


def _zone_hotspot_score(db: Session, zone_id: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=30)

    total = (
        db.query(func.count(Claim.id))
        .join(Disruption, Disruption.id == Claim.disruption_id)
        .filter(Disruption.zone_id == zone_id, Claim.created_at >= start_time)
        .scalar()
        or 0
    )
    suspicious = (
        db.query(func.count(Claim.id))
        .join(Disruption, Disruption.id == Claim.disruption_id)
        .filter(
            Disruption.zone_id == zone_id,
            Claim.created_at >= start_time,
            (Claim.audit_required.is_(True)) | (Claim.status.in_([ClaimStatusEnum.held, ClaimStatusEnum.rejected])),
        )
        .scalar()
        or 0
    )

    if total <= 0:
        return 0.0, reasons

    ratio = suspicious / total
    score = _clamp(ratio * 100.0)
    if ratio >= 0.35:
        reasons.append(f"Zone hotspot risk is elevated ({ratio:.0%} suspicious claims)")
    return score, reasons


def _cluster_anomaly_score(db: Session, worker: Worker) -> tuple[float, list[str]]:
    reasons: list[str] = []
    rows = (
        db.query(Worker)
        .all()
    )

    if len(rows) < 3:
        return 0.0, reasons

    feature_rows: list[list[float]] = []
    worker_index_map: dict[str, int] = {}
    for idx, item in enumerate(rows):
        recent_claims = (
            db.query(Claim)
            .filter(Claim.worker_id == item.id)
            .order_by(Claim.created_at.desc())
            .limit(12)
            .all()
        )
        if not recent_claims:
            avg_baf = 0.5
            audit_rate = 0.0
            held_rate = 0.0
            mismatch_rate = 0.0
        else:
            avg_baf = float(np.mean([float(c.baf_score or 0.5) for c in recent_claims]))
            audit_rate = float(np.mean([1.0 if c.audit_required else 0.0 for c in recent_claims]))
            held_rate = float(np.mean([1.0 if c.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected} else 0.0 for c in recent_claims]))
            mismatch_rate = float(np.mean([min(float(c.spoofing_signals_fired or 0) / 5.0, 1.0) for c in recent_claims]))

        feature_rows.append([avg_baf, audit_rate, held_rate, mismatch_rate])
        worker_index_map[str(item.id)] = idx

    k = min(3, len(feature_rows))
    if k < 2:
        return 0.0, reasons

    matrix = np.array(feature_rows)
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = model.fit_predict(matrix)
    centers = model.cluster_centers_

    risk_by_cluster: dict[int, float] = {}
    for cidx in range(k):
        center = centers[cidx]
        risk = _clamp((1.0 - center[0]) * 45.0 + center[1] * 30.0 + center[2] * 20.0 + center[3] * 25.0)
        risk_by_cluster[cidx] = risk

    worker_idx = worker_index_map.get(str(worker.id))
    if worker_idx is None:
        return 0.0, reasons

    worker_cluster = int(labels[worker_idx])
    score = risk_by_cluster.get(worker_cluster, 0.0)
    if score >= 45.0:
        reasons.append("Worker behavior aligns with a suspicious behavior cluster")

    return score, reasons


def _worker_similarity_score(db: Session, worker: Worker) -> tuple[float, list[str]]:
    reasons: list[str] = []
    recent_claims = (
        db.query(Claim)
        .join(Disruption, Disruption.id == Claim.disruption_id)
        .filter(Claim.worker_id == worker.id)
        .order_by(Claim.created_at.desc())
        .limit(12)
        .all()
    )

    if not recent_claims:
        return 0.0, reasons

    worker_vector = np.array([
        float(worker.trust_score),
        float(worker.tenure_weeks) / 60.0,
        float(worker.avg_weekly_income or 0.0) / 1000.0,
        float(np.mean([float(c.baf_score or 0.5) for c in recent_claims])),
        float(np.mean([1.0 if c.audit_required else 0.0 for c in recent_claims])),
        float(np.mean([1.0 if c.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected} else 0.0 for c in recent_claims])),
    ], dtype=np.float64)

    suspicious_rows = (
        db.query(Worker)
        .join(Claim, Claim.worker_id == Worker.id)
        .filter(Claim.audit_required.is_(True) | Claim.status.in_([ClaimStatusEnum.held, ClaimStatusEnum.rejected]))
        .all()
    )

    if not suspicious_rows:
        return 0.0, reasons

    cluster_vectors = []
    for other in suspicious_rows[:32]:
        other_claims = (
            db.query(Claim)
            .filter(Claim.worker_id == other.id)
            .order_by(Claim.created_at.desc())
            .limit(12)
            .all()
        )
        if not other_claims:
            continue
        cluster_vectors.append(np.array([
            float(other.trust_score),
            float(other.tenure_weeks) / 60.0,
            float(other.avg_weekly_income or 0.0) / 1000.0,
            float(np.mean([float(c.baf_score or 0.5) for c in other_claims])),
            float(np.mean([1.0 if c.audit_required else 0.0 for c in other_claims])),
            float(np.mean([1.0 if c.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected} else 0.0 for c in other_claims])),
        ], dtype=np.float64))

    if not cluster_vectors:
        return 0.0, reasons

    centroid = np.mean(cluster_vectors, axis=0)
    denominator = float(np.linalg.norm(worker_vector) * np.linalg.norm(centroid))
    similarity = float(np.dot(worker_vector, centroid) / denominator) if denominator > 0 else 0.0
    score = _clamp(max(similarity, 0.0) * 100.0)
    if score >= 55.0:
        reasons.append("Worker behavior is similar to suspicious worker clusters")

    return score, reasons


def _claim_anomaly_second_opinion(db: Session, worker: Worker, claim_metadata: dict, spoof_result: dict, baf_score: float) -> tuple[float, list[str]]:
    reasons: list[str] = []
    historical_claims = (
        db.query(Claim)
        .filter(Claim.worker_id == worker.id)
        .order_by(Claim.created_at.desc())
        .limit(30)
        .all()
    )

    if len(historical_claims) < 8:
        return 0.0, reasons

    rows = []
    for claim in historical_claims:
        rows.append([
            float(claim.baf_score or 0.5),
            float(claim.signal_confidence or 0.5),
            float(claim.behavior_confidence or 0.5),
            float(claim.unified_confidence or 0.5),
            float(claim.spoofing_signals_fired or 0),
            1.0 if claim.audit_required else 0.0,
        ])

    current_row = np.array([
        float(baf_score),
        float(1.0 - float(claim_metadata.get("gps_confidence", 0.0))),
        float(claim_metadata.get("acceptance_drop", 0.0)),
        float(claim_metadata.get("online_hours_during", 0.0)) / 12.0,
        float(spoof_result.get("spoofing_signals_fired", 0)),
        1.0 if bool(claim_metadata.get("gps_mismatch", False)) else 0.0,
    ], dtype=np.float64)

    try:
        model_backend = settings.fraud_anomaly_model_backend
        x_train = np.array(rows, dtype=np.float64)
        x_test = current_row.reshape(1, -1)

        if model_backend == "one_class_svm":
            scaler = StandardScaler()
            x_train = scaler.fit_transform(x_train)
            x_test = scaler.transform(x_test)
            model = OneClassSVM(kernel="rbf", gamma="scale", nu=0.08)
            model.fit(x_train)
            anomaly = float(abs(model.decision_function(x_test)[0]))
            score = _clamp(anomaly * 120.0)
        else:
            model = IsolationForest(random_state=42, contamination="auto", n_estimators=100)
            model.fit(x_train)
            anomaly = -float(model.score_samples(x_test)[0])
            score = _clamp(anomaly * 100.0)
        if score >= 50.0:
            reasons.append(f"Second-opinion anomaly model ({model_backend}) flagged this claim")
        return score, reasons
    except Exception:
        return 0.0, reasons


def _fine_zone_granularity_score(claim_metadata: dict, claimed_zone_id: str) -> tuple[float, list[str]]:
    reasons: list[str] = []

    gps_parent_zone = str(claim_metadata.get("gps_zone", "") or "")
    ip_parent_zone = str(claim_metadata.get("ip_zone", "") or "")
    gps_fine_zone = claim_metadata.get("gps_micro_zone")
    ip_fine_zone = claim_metadata.get("ip_micro_zone")

    score = 0.0

    if gps_parent_zone and parent_zone_for(gps_parent_zone) != parent_zone_for(claimed_zone_id):
        score += 55.0
        reasons.append("Fine-zone GPS parent does not match claimed zone")
    elif gps_fine_zone:
        score += 12.0

    if ip_parent_zone and parent_zone_for(ip_parent_zone) != parent_zone_for(claimed_zone_id):
        score += 35.0
        reasons.append("Fine-zone IP parent does not match claimed zone")

    if gps_fine_zone and ip_fine_zone and gps_fine_zone != ip_fine_zone:
        score += 18.0
        reasons.append("GPS and IP fine-zone sectors disagree")

    return _clamp(score), reasons


def _zone_occupancy_score(db: Session, worker: Worker, claimed_zone_id: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)

    traces = (
        db.query(WorkerLocationTrace)
        .filter(
            WorkerLocationTrace.worker_id == worker.id,
            WorkerLocationTrace.created_at >= start_time,
        )
        .order_by(WorkerLocationTrace.created_at.asc())
        .all()
    )

    if len(traces) < 2:
        return 15.0, ["Limited recent location traces available"]

    claimed_parent = parent_zone_for(claimed_zone_id)
    in_claimed = [
        t for t in traces
        if t.mapped_parent_zone_id and parent_zone_for(str(t.mapped_parent_zone_id)) == claimed_parent
    ]
    ratio = len(in_claimed) / max(len(traces), 1)

    score = _clamp((1.0 - ratio) * 100.0)
    if ratio < 0.35:
        reasons.append("Low 24h location presence in claimed zone")
    elif ratio > 0.7:
        score = max(score - 20.0, 0.0)

    return score, reasons


def _llm_explanation_or_fallback(assessment: dict) -> tuple[str, float, str]:
    fallback = (
        f"Fraud risk score is {assessment['fraud_score']:.1f}/100 ({assessment['fraud_band']}). "
        f"Top reasons: {', '.join(assessment['top_reasons'][:3]) or 'No dominant signals'}."
    )

    if not settings.fraud_llm_enabled or not settings.fraud_llm_api_key:
        return fallback, 0.74, "template"

    prompt = {
        "task": "Explain fraud decision briefly for operations analyst",
        "fraud_score": round(float(assessment["fraud_score"]), 2),
        "fraud_band": assessment["fraud_band"],
        "component_scores": assessment["component_scores"],
        "top_reasons": assessment["top_reasons"],
    }

    body = {
        "model": settings.fraud_llm_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a fraud analyst assistant. Keep explanations concise and evidence-based.",
            },
            {
                "role": "user",
                "content": json.dumps(prompt),
            },
        ],
        "temperature": 0.2,
    }

    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.post(
                settings.fraud_llm_endpoint,
                headers={
                    "Authorization": f"Bearer {settings.fraud_llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            if text:
                return text, 0.82, settings.fraud_llm_model
    except Exception:
        pass

    return fallback, 0.74, "template"


def assess_claim_fraud(
    *,
    db: Session,
    worker: Worker,
    disruption: Disruption,
    claim_metadata: dict,
    spoof_result: dict,
    baf_score: float,
) -> FraudAssessment:
    """Compute ensemble fraud score and explanation for one claim."""
    gps_mismatch = 1.0 if bool(claim_metadata.get("gps_mismatch", False)) else 0.0
    ip_mismatch = 1.0 if bool(claim_metadata.get("ip_mismatch", False)) else 0.0
    behavior_anomaly = _clamp((float(claim_metadata.get("acceptance_drop", 0.0)) * 140.0) + ((1.0 - float(baf_score)) * 35.0))

    conflict_score, conflict_reasons = _cross_signal_conflict_score(claim_metadata=claim_metadata, spoof_result=spoof_result)
    fine_zone_score, fine_zone_reasons = _fine_zone_granularity_score(
        claim_metadata=claim_metadata,
        claimed_zone_id=disruption.zone_id,
    )
    occupancy_score, occupancy_reasons = _zone_occupancy_score(
        db=db,
        worker=worker,
        claimed_zone_id=disruption.zone_id,
    )
    hotspot_score, hotspot_reasons = _zone_hotspot_score(db=db, zone_id=disruption.zone_id)
    cluster_score, cluster_reasons = _cluster_anomaly_score(db=db, worker=worker)
    similarity_score, similarity_reasons = _worker_similarity_score(db=db, worker=worker)
    anomaly_score, anomaly_reasons = _claim_anomaly_second_opinion(
        db=db,
        worker=worker,
        claim_metadata=claim_metadata,
        spoof_result=spoof_result,
        baf_score=baf_score,
    )
    historical_score, historical_reasons = _historical_fraud_likelihood(
        db=db,
        worker=worker,
        disruption=disruption,
        claim_metadata=claim_metadata,
        baf_score=baf_score,
    )
    zone_pressure_score = float(claim_metadata.get("disruption_context", {}).get("severity_index", 0.0)) * 100.0

    weighted_score = (
        0.28 * (gps_mismatch * 100.0)
        + 0.22 * behavior_anomaly
        + 0.15 * (ip_mismatch * 100.0)
        + 0.12 * fine_zone_score
        + 0.10 * occupancy_score
        + 0.12 * conflict_score
        + 0.09 * hotspot_score
        + 0.07 * historical_score
    )

    if disruption.disruption_type.value in {"rainfall", "flood"}:
        weighted_score += 5.0 * gps_mismatch
    if disruption.disruption_type.value in {"platform_outage", "curfew"}:
        weighted_score += 4.0 * (behavior_anomaly / 100.0)

    weighted_score += 0.10 * cluster_score
    weighted_score += 0.08 * similarity_score
    weighted_score += 0.06 * anomaly_score
    weighted_score += 0.05 * zone_pressure_score
    fraud_score = _clamp(weighted_score)
    fraud_band = _risk_band(fraud_score)

    reasons = [
        *conflict_reasons,
        *fine_zone_reasons,
        *occupancy_reasons,
        *hotspot_reasons,
        *cluster_reasons,
        *similarity_reasons,
        *anomaly_reasons,
        *historical_reasons,
    ]
    if gps_mismatch:
        reasons.append("GPS location mismatch with claimed zone")
    if ip_mismatch:
        reasons.append("IP geolocation mismatch with claimed zone")
    if behavior_anomaly >= 45.0:
        reasons.append("Behavioral activity drop is inconsistent")

    unique_reasons: list[str] = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)

    if not unique_reasons:
        unique_reasons = ["No material anomaly detected"]

    component_scores = {
        "gps_mismatch_score": round(gps_mismatch * 100.0, 2),
        "behavior_anomaly_score": round(behavior_anomaly, 2),
        "ip_mismatch_score": round(ip_mismatch * 100.0, 2),
        "fine_zone_score": round(fine_zone_score, 2),
        "zone_occupancy_score": round(occupancy_score, 2),
        "cross_signal_conflict_score": round(conflict_score, 2),
        "zone_hotspot_score": round(hotspot_score, 2),
        "historical_pattern_score": round(historical_score, 2),
        "cluster_anomaly_score": round(cluster_score, 2),
        "worker_similarity_score": round(similarity_score, 2),
        "claim_anomaly_score": round(anomaly_score, 2),
        "zone_pressure_score": round(zone_pressure_score, 2),
    }

    explanation, explanation_confidence, explanation_source = _llm_explanation_or_fallback(
        {
            "fraud_score": fraud_score,
            "fraud_band": fraud_band,
            "component_scores": component_scores,
            "top_reasons": unique_reasons,
        }
    )

    return FraudAssessment(
        fraud_score=round(fraud_score, 2),
        fraud_band=fraud_band,
        component_scores=component_scores,
        top_reasons=unique_reasons[:5],
        explanation=explanation,
        explanation_confidence=round(explanation_confidence, 3),
        explanation_source=explanation_source,
    )


def admin_fraud_payload(claim: Claim) -> dict:
    """Build admin-only fraud fields from persisted claim values."""
    inferred_fraud_score = float(claim.fraud_score) if claim.fraud_score is not None else None
    if inferred_fraud_score is None:
        inferred_fraud_score = round((1.0 - float(claim.signal_confidence or 0.0)) * 100.0, 2)

    explanation = claim.fraud_explanation or claim.audit_reason
    explanation_source = claim.fraud_explanation_source or "audit_reason"
    explanation_confidence = claim.fraud_explanation_confidence
    component_scores = claim.fraud_component_scores or {}
    top_reasons = claim.fraud_top_reasons or []

    return {
        "fraud_score": inferred_fraud_score,
        "fraud_band": claim.fraud_band or _risk_band(inferred_fraud_score),
        "fraud_explanation": explanation,
        "fraud_explanation_confidence": explanation_confidence,
        "fraud_explanation_source": explanation_source,
        "fraud_component_scores": component_scores,
        "fraud_top_reasons": top_reasons,
    }