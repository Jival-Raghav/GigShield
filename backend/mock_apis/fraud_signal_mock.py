"""Mock telemetry APIs for fraud signal simulation."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone


def _seeded_rng(worker_id: str, zone_id: str, salt: str) -> random.Random:
    digest = hashlib.sha256(f"{worker_id}:{zone_id}:{salt}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def get_gps_signal(worker_id: str, claimed_zone_id: str, home_zone_id: str) -> dict:
    """Return mock GPS zone and confidence snapshot for a worker claim."""
    rng = _seeded_rng(worker_id, claimed_zone_id, "gps")

    mismatch_prob = 0.12 if claimed_zone_id == home_zone_id else 0.28
    is_mismatch = rng.random() < mismatch_prob
    gps_zone = f"{claimed_zone_id}-edge" if is_mismatch else claimed_zone_id
    gps_confidence = round(rng.uniform(0.55, 0.97), 3)

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "gps_zone": gps_zone,
        "gps_confidence": gps_confidence,
        "source": "GPS_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }


def get_cell_tower_signal(worker_id: str, claimed_zone_id: str) -> dict:
    """Return mock cell tower based zone estimation."""
    rng = _seeded_rng(worker_id, claimed_zone_id, "cell")
    mismatch_prob = 0.14
    cell_zone = f"{claimed_zone_id}-adjacent" if rng.random() < mismatch_prob else claimed_zone_id

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "cell_tower_zone": cell_zone,
        "source": "CELL_TOWER_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }


def get_ip_geolocation_signal(worker_id: str, claimed_zone_id: str) -> dict:
    """Return mock IP based zone estimate."""
    rng = _seeded_rng(worker_id, claimed_zone_id, "ip")
    mismatch_prob = 0.2
    ip_zone = f"{claimed_zone_id}-vpn" if rng.random() < mismatch_prob else claimed_zone_id

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "ip_zone": ip_zone,
        "source": "IP_GEO_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }


def get_motion_signal(worker_id: str, claimed_zone_id: str) -> dict:
    """Return mock accelerometer motion signal."""
    rng = _seeded_rng(worker_id, claimed_zone_id, "motion")
    is_stationary = rng.random() < 0.22

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "is_stationary": is_stationary,
        "source": "ACCELEROMETER_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }


def get_order_activity_signal(worker_id: str, claimed_zone_id: str, disruption_severity: float) -> dict:
    """Return mock order acceptance and online-hours snapshot."""
    rng = _seeded_rng(worker_id, claimed_zone_id, "activity")
    severity = max(0.0, min(disruption_severity, 1.0))

    acceptance_base = 0.64 - (severity * 0.22)
    acceptance = max(0.05, min(0.95, acceptance_base + rng.uniform(-0.18, 0.18)))

    online_base = 8.0 - (severity * 3.0)
    online_hours = max(0.5, min(12.0, online_base + rng.uniform(-2.0, 2.0)))

    return {
        "worker_id": worker_id,
        "zone_id": claimed_zone_id,
        "acceptance_rate_during": round(acceptance, 3),
        "online_hours_during": round(online_hours, 2),
        "source": "ORDER_ACTIVITY_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }
