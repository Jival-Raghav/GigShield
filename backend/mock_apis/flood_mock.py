"""Mock flood alert APIs for demo trigger simulation."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone


def _seeded_rng(zone_id: str) -> random.Random:
    digest = hashlib.sha256(f"{zone_id}:flood".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def get_flood_alert(zone_id: str) -> dict:
    """
    Return mock flood alert status.

    Returns:
    {
      "zone_id": str,
      "alert_active": bool,
      "alert_level": str,
        ("none"/"watch"/"warning"/"emergency")
      "source": "NDMA_MOCK",
      "timestamp": datetime
    }
    """
    rng = _seeded_rng(zone_id)
    score = rng.random()

    if score < 0.55:
        alert_level = "none"
    elif score < 0.75:
        alert_level = "watch"
    elif score < 0.9:
        alert_level = "warning"
    else:
        alert_level = "emergency"

    if any(key in zone_id.lower() for key in ["flood", "coastal", "river"]):
        alert_level = "warning" if alert_level in {"none", "watch"} else alert_level

    return {
        "zone_id": zone_id,
        "alert_active": alert_level != "none",
        "alert_level": alert_level,
        "source": "NDMA_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }
