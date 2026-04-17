"""Mock civic curfew API for trigger simulation."""

from __future__ import annotations

import logging
import hashlib
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _seeded_rng(zone_id: str) -> random.Random:
    digest = hashlib.sha256(f"{zone_id}:curfew".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def get_curfew_status(zone_id: str) -> dict:
    """Return mock curfew status for a zone."""
    logger.warning("Using mock curfew data for zone %s.", zone_id)
    rng = _seeded_rng(zone_id)
    score = rng.random()

    if score < 0.7:
        level = "none"
    elif score < 0.9:
        level = "night"
    else:
        level = "full"

    if any(key in zone_id.lower() for key in ["sensitive", "central", "event"]):
        if level == "none":
            level = "night"

    return {
        "zone_id": zone_id,
        "curfew_active": level != "none",
        "curfew_level": level,
        "source": "CIVIC_CURFEW_MOCK",
        "timestamp": datetime.now(timezone.utc),
    }
