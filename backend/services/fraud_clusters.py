"""Behavior cluster summaries for the admin fraud map."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy.orm import Session

from models.claim import Claim, ClaimStatusEnum
from models.disruption import Disruption
from models.worker import Worker
from services.zone_granularity import parent_zone_for


def _feature_vector(db: Session, worker: Worker) -> list[float]:
    recent_claims = (
        db.query(Claim)
        .filter(Claim.worker_id == worker.id)
        .order_by(Claim.created_at.desc())
        .limit(20)
        .all()
    )
    if not recent_claims:
        return [
            float(worker.trust_score),
            float(worker.tenure_weeks) / 52.0,
            float(worker.avg_weekly_income or 0.0) / 1000.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

    baf_scores = [float(item.baf_score or 0.5) for item in recent_claims]
    audit_rate = [1.0 if item.audit_required else 0.0 for item in recent_claims]
    negative_rate = [1.0 if item.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected} else 0.0 for item in recent_claims]
    spoof_rate = [min(float(item.spoofing_signals_fired or 0) / 5.0, 1.0) for item in recent_claims]
    payout_avg = [float(item.payout_amount or 0.0) / max(float(worker.avg_weekly_income or 1.0), 1.0) for item in recent_claims]

    return [
        float(worker.trust_score),
        float(worker.tenure_weeks) / 52.0,
        float(worker.avg_weekly_income or 0.0) / 1000.0,
        float(np.mean(baf_scores)),
        float(np.mean(audit_rate)),
        float(np.mean(negative_rate)),
        float(np.mean(spoof_rate) + np.mean(payout_avg)),
    ]


def _cluster_label(cluster_row: dict[str, float]) -> str:
    if cluster_row["suspicious_claim_ratio"] >= 0.6:
        return "High fraud pressure"
    if cluster_row["avg_audit_rate"] >= 0.45:
        return "Audit-heavy cluster"
    if cluster_row["avg_claim_frequency"] >= 4.0:
        return "High frequency cluster"
    if cluster_row["avg_trust_score"] >= 0.72:
        return "Low-risk trusted cluster"
    return "Mixed behavior cluster"


def build_fraud_cluster_map(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=60)

    workers = db.query(Worker).all()
    if len(workers) < 3:
        return {"generated_at": now.isoformat(), "clusters": [], "zones": [], "total_workers": len(workers), "total_claims": 0}

    recent_claims = db.query(Claim).filter(Claim.created_at >= cutoff).all()
    worker_features = np.array([_feature_vector(db, worker) for worker in workers], dtype=np.float64)
    n_clusters = min(4, len(workers))
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(worker_features)

    worker_lookup = {str(worker.id): index for index, worker in enumerate(workers)}
    worker_cluster_map = {str(worker.id): int(labels[index]) for index, worker in enumerate(workers)}

    claims_by_worker: dict[str, list[Claim]] = defaultdict(list)
    for claim in recent_claims:
        claims_by_worker[str(claim.worker_id)].append(claim)

    cluster_buckets: dict[int, dict] = defaultdict(lambda: {
        "workers": [],
        "zones": Counter(),
        "trust_scores": [],
        "claim_counts": [],
        "audit_rates": [],
        "negative_rates": [],
        "spoof_rates": [],
        "baf_scores": [],
        "recent_claims": [],
    })

    zone_buckets: dict[str, dict] = defaultdict(lambda: {
        "workers": set(),
        "cluster_counts": Counter(),
        "claims": [],
        "trust_scores": [],
    })

    for worker in workers:
        cluster_id = worker_cluster_map[str(worker.id)]
        recent_worker_claims = claims_by_worker.get(str(worker.id), [])
        bucket = cluster_buckets[cluster_id]
        bucket["workers"].append(worker)
        bucket["zones"][worker.micro_zone_id] += 1
        bucket["trust_scores"].append(float(worker.trust_score))
        bucket["claim_counts"].append(len(recent_worker_claims))
        bucket["audit_rates"].append(float(np.mean([1.0 if item.audit_required else 0.0 for item in recent_worker_claims])) if recent_worker_claims else 0.0)
        bucket["negative_rates"].append(float(np.mean([1.0 if item.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected} else 0.0 for item in recent_worker_claims])) if recent_worker_claims else 0.0)
        bucket["spoof_rates"].append(float(np.mean([min(float(item.spoofing_signals_fired or 0) / 5.0, 1.0) for item in recent_worker_claims])) if recent_worker_claims else 0.0)
        bucket["baf_scores"].append(float(np.mean([float(item.baf_score or 0.5) for item in recent_worker_claims])) if recent_worker_claims else 0.5)
        bucket["recent_claims"].extend(recent_worker_claims[:6])

        zone_bucket = zone_buckets[worker.micro_zone_id]
        zone_bucket["workers"].add(str(worker.id))
        zone_bucket["cluster_counts"][cluster_id] += 1
        zone_bucket["claims"].extend(recent_worker_claims)
        zone_bucket["trust_scores"].append(float(worker.trust_score))

    clusters: list[dict] = []
    for cluster_id, bucket in cluster_buckets.items():
        avg_trust = float(np.mean(bucket["trust_scores"])) if bucket["trust_scores"] else 0.0
        avg_audit_rate = float(np.mean(bucket["audit_rates"])) if bucket["audit_rates"] else 0.0
        avg_negative_rate = float(np.mean(bucket["negative_rates"])) if bucket["negative_rates"] else 0.0
        avg_spoof_rate = float(np.mean(bucket["spoof_rates"])) if bucket["spoof_rates"] else 0.0
        avg_baf = float(np.mean(bucket["baf_scores"])) if bucket["baf_scores"] else 0.5
        avg_claim_frequency = float(np.mean(bucket["claim_counts"])) if bucket["claim_counts"] else 0.0
        suspicious_claim_ratio = float(np.clip((avg_audit_rate * 0.55) + (avg_negative_rate * 0.3) + (avg_spoof_rate * 0.15), 0.0, 1.0))
        cluster_score = round(min(100.0, (1.0 - avg_trust) * 38.0 + suspicious_claim_ratio * 100.0 + avg_claim_frequency * 4.0), 2)
        top_zones = [zone for zone, _ in bucket["zones"].most_common(3)]
        top_worker_names = [worker.name for worker in sorted(bucket["workers"], key=lambda item: item.trust_score)[:4]]
        top_claim_reasons = []
        for claim in bucket["recent_claims"][:6]:
            if claim.audit_reason:
                top_claim_reasons.append(claim.audit_reason)
        clusters.append({
            "cluster_id": f"cluster_{cluster_id}",
            "size": len(bucket["workers"]),
            "avg_trust_score": round(avg_trust, 3),
            "avg_baf_score": round(avg_baf, 3),
            "avg_audit_rate": round(avg_audit_rate, 3),
            "avg_negative_rate": round(avg_negative_rate, 3),
            "avg_claim_frequency": round(avg_claim_frequency, 2),
            "suspicious_claim_ratio": round(suspicious_claim_ratio, 3),
            "cluster_score": cluster_score,
            "behavior_label": _cluster_label({
                "suspicious_claim_ratio": suspicious_claim_ratio,
                "avg_audit_rate": avg_audit_rate,
                "avg_claim_frequency": avg_claim_frequency,
                "avg_trust_score": avg_trust,
            }),
            "top_zones": top_zones,
            "top_worker_names": top_worker_names,
            "top_reasons": list(dict.fromkeys(top_claim_reasons))[:4],
        })

    clusters.sort(key=lambda row: row["cluster_score"], reverse=True)

    zones: list[dict] = []
    for zone_id, bucket in zone_buckets.items():
        worker_count = len(bucket["workers"])
        claim_count = len(bucket["claims"])
        suspicious_count = len([claim for claim in bucket["claims"] if claim.audit_required or claim.status in {ClaimStatusEnum.held, ClaimStatusEnum.rejected}])
        avg_fraud_score = float(np.mean([(1.0 - float(claim.signal_confidence or 0.0)) * 100.0 for claim in bucket["claims"]])) if bucket["claims"] else 0.0
        dominant_cluster = bucket["cluster_counts"].most_common(1)[0][0] if bucket["cluster_counts"] else 0
        zones.append({
            "zone_id": zone_id,
            "parent_zone_id": parent_zone_for(zone_id),
            "worker_count": worker_count,
            "claim_count": claim_count,
            "suspicious_claim_count": suspicious_count,
            "suspicious_claim_ratio": round(suspicious_count / max(claim_count, 1), 3),
            "avg_trust_score": round(float(np.mean(bucket["trust_scores"])) if bucket["trust_scores"] else 0.0, 3),
            "avg_fraud_score": round(avg_fraud_score, 2),
            "dominant_cluster": f"cluster_{dominant_cluster}",
            "cluster_size": int(bucket["cluster_counts"].get(dominant_cluster, 0)),
        })

    zones.sort(key=lambda row: (row["suspicious_claim_ratio"], row["avg_fraud_score"]), reverse=True)

    return {
        "generated_at": now.isoformat(),
        "total_workers": len(workers),
        "total_claims": len(recent_claims),
        "clusters": clusters,
        "zones": zones,
    }