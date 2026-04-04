"""Mock AQI APIs for demo trigger simulation."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone


def _seeded_rng(zone_id: str) -> random.Random:
    digest = hashlib.sha256(f"{zone_id}:aqi".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def get_aqi(zone_id: str) -> dict:
    """
    Return mock AQI data.
    Returns AQI value between 0-500.

    Returns:
    {
      "zone_id": str,
      "aqi": int,
      "category": str,
        ("good"/"moderate"/"poor"/"severe")
      "source": "CPCB_MOCK",
      "timestamp": datetime
    }
    """
    rng = _seeded_rng(zone_id)
    aqi = int(rng.uniform(20, 480))

    if aqi <= 100:
        category = "good"
    elif aqi <= 200:
        category = "moderate"
    elif aqi <= 300:
        category = "poor"
    else:
        category = "severe"

    return {
        "zone_id": zone_id,
        "aqi": aqi,
        "category": category,
        "source": "CPCB_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }
