"""Mock weather APIs for demo trigger simulation."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone


def _seeded_rng(zone_id: str, salt: str) -> random.Random:
    digest = hashlib.sha256(f"{zone_id}:{salt}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def get_rainfall(zone_id: str) -> dict:
    """
    Return mock rainfall data for a zone.
    Randomly return values between 0-150mm/hr.
    Some zones should consistently return high values
    (use zone_id to seed the random for consistency).

    Returns:
    {
      "zone_id": str,
      "rainfall_mm_per_hr": float,
      "source": "IMD_MOCK",
      "timestamp": datetime
    }
    """
    rng = _seeded_rng(zone_id, "rainfall")
    base = rng.uniform(0, 150)
    if any(key in zone_id.lower() for key in ["high", "flood", "coastal", "river"]):
        base = min(150.0, base + 35.0)

    event_end = datetime.now(timezone.utc)
    event_duration_hours = 1.0
    event_start = event_end - timedelta(hours=event_duration_hours)

    return {
        "zone_id": zone_id,
        "rainfall_mm_per_hr": round(base, 2),
        "duration_hours": event_duration_hours,
        "event_started_at": event_start,
        "event_ended_at": event_end,
        "source": "IMD_MOCK",
        "timestamp": event_end,
    }


def get_temperature(zone_id: str) -> dict:
    """
    Return mock temperature/weather data.
    Returns temp in Celsius and weather condition.

    Returns:
    {
      "zone_id": str,
      "temperature_celsius": float,
      "condition": str,
        ("clear"/"rain"/"heavy_rain"/"flood")
      "source": "IMD_MOCK",
      "timestamp": datetime
    }
    """
    rng = _seeded_rng(zone_id, "temperature")
    temp = rng.uniform(18.0, 44.0)
    rainfall = get_rainfall(zone_id)["rainfall_mm_per_hr"]

    if rainfall > 100:
        condition = "flood"
    elif rainfall > 65:
        condition = "heavy_rain"
    elif rainfall > 20:
        condition = "rain"
    else:
        condition = "clear"

    return {
        "zone_id": zone_id,
        "temperature_celsius": round(temp, 1),
        "condition": condition,
        "source": "IMD_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }
