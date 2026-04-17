"""AQI API integration using WAQI (aqicn.org) — India city data via CPCB stations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from config import settings
from services.zone_granularity import parent_zone_for

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# City-to-WAQI-feed mapping for common Indian zone_id patterns.
# WAQI uses city/station slugs in its feed endpoint.
# ---------------------------------------------------------------------------
_PARENT_ZONE_TO_WAQI_CITY: dict[str, str] = {
    "BLR_KORAMANGALA_004": "bengaluru",
    "PUN_KOTHRUD_002": "pune",
    "HYD_GACHIBOWLI_007": "hyderabad",
}

_ZONE_TO_WAQI_CITY: dict[str, str] = {
    "delhi": "delhi",
    "mumbai": "mumbai",
    "bengaluru": "bengaluru",
    "bangalore": "bengaluru",
    "chennai": "chennai",
    "kolkata": "kolkata",
    "hyderabad": "hyderabad",
    "pune": "pune",
    "ahmedabad": "ahmedabad",
    "surat": "surat",
    "jaipur": "jaipur",
    "lucknow": "lucknow",
    "kanpur": "kanpur",
    "nagpur": "nagpur",
    "patna": "patna",
    "bhopal": "bhopal",
    "indore": "indore",
    "visakhapatnam": "visakhapatnam",
    "vadodara": "vadodara",
    "agra": "agra",
}

_WAQI_BASE = "https://api.waqi.info/feed"
_REQUEST_TIMEOUT = 8  # seconds


def _resolve_city(zone_id: str) -> str:
    """Map a zone_id string to a WAQI city slug for India."""
    parent_zone_id = parent_zone_for(zone_id)
    if parent_zone_id in _PARENT_ZONE_TO_WAQI_CITY:
        return _PARENT_ZONE_TO_WAQI_CITY[parent_zone_id]

    z = zone_id.lower()
    for key, city in _ZONE_TO_WAQI_CITY.items():
        if key in z:
            return city
    # Fall back: use the first token of zone_id as-is (WAQI handles many names)
    return z.split("_")[0].split("-")[0]


def _aqi_category(aqi: int) -> str:
    if aqi <= 100:
        return "good"
    elif aqi <= 200:
        return "moderate"
    elif aqi <= 300:
        return "poor"
    else:
        return "severe"


def get_aqi(zone_id: str) -> dict:
    """
    Return live AQI data from WAQI (aqicn.org) for an Indian city
    mapped from zone_id.

    Requires WAQI_API_TOKEN environment variable.
    Falls back to a degraded response (aqi=-1) if the API is unreachable
    or the token is missing.

    Returns:
    {
      "zone_id": str,
      "aqi": int,
      "category": str,
        ("good"/"moderate"/"poor"/"severe")
      "source": "CPCB_WAQI",
      "timestamp": datetime
    }
    """
    token = settings.waqi_api_token.strip()
    city = _resolve_city(zone_id)
    now = datetime.now(timezone.utc)

    if not token:
        logger.warning("Using mock AQI data for zone %s because WAQI_API_TOKEN is not set.", zone_id)
        return {
            "zone_id": zone_id,
            "aqi": -1,
            "category": "unknown",
            "source": "CPCB_WAQI",
            "timestamp": now,
            "error": "WAQI_API_TOKEN not configured",
        }

    url = f"{_WAQI_BASE}/{city}/?token={token}"
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            raise ValueError(f"WAQI returned status={data.get('status')} for city={city!r}")

        raw_aqi = data["data"]["aqi"]
        # WAQI sometimes returns "-" for stations with no data
        aqi = int(raw_aqi) if str(raw_aqi).lstrip("-").isdigit() else -1

        return {
            "zone_id": zone_id,
            "aqi": aqi,
            "category": _aqi_category(aqi) if aqi >= 0 else "unknown",
            "source": "CPCB_WAQI",
            "timestamp": now,
        }

    except requests.RequestException as exc:
        logger.warning("Using mock AQI data for zone %s because WAQI request failed: %s", zone_id, exc)
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Using mock AQI data for zone %s because WAQI response parsing failed: %s", zone_id, exc)

    # Graceful degraded fallback
    logger.warning("Using mock AQI data for zone %s.", zone_id)
    return {
        "zone_id": zone_id,
        "aqi": -1,
        "category": "unknown",
        "source": "CPCB_WAQI",
        "timestamp": now,
        "error": "API call failed",
    }
