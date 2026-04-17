"""Mock platform outage API for trigger simulation."""

from __future__ import annotations

import logging
import hashlib
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _seeded_rng(zone_id: str) -> random.Random:
    digest = hashlib.sha256(f"{zone_id}:platform".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def get_platform_status(zone_id: str) -> dict:
    """Return mock platform health snapshot for a zone."""
    logger.warning("Using mock platform outage data for zone %s.", zone_id)
    rng = _seeded_rng(zone_id)
    uptime_percent = round(rng.uniform(90.0, 100.0), 2)
    api_error_rate = round(rng.uniform(0.0, 0.25), 3)

    if any(key in zone_id.lower() for key in ["downtown", "dense", "peak"]):
        api_error_rate = min(0.35, api_error_rate + 0.08)
        uptime_percent = max(80.0, uptime_percent - 3.0)

    outage_active = api_error_rate >= 0.12 or uptime_percent <= 95.0

    return {
        "zone_id": zone_id,
        "outage_active": outage_active,
        "api_error_rate": api_error_rate,
        "uptime_percent": uptime_percent,
        "source": "PLATFORM_HEALTH_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }
