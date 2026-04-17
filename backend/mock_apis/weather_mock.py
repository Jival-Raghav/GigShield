"""Weather API integration using Open-Meteo — free, no API key, India-specific."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from services.zone_granularity import zone_coordinates_for

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Coordinates for major Indian cities / zone patterns.
# Open-Meteo uses lat/lon, so we map zone_id tokens to coordinates.
# ---------------------------------------------------------------------------
_ZONE_COORDS: dict[str, tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "ahmedabad": (23.0225, 72.5714),
    "surat": (21.1702, 72.8311),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462),
    "kanpur": (26.4499, 80.3319),
    "nagpur": (21.1458, 79.0882),
    "patna": (25.5941, 85.1376),
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "visakhapatnam": (17.6868, 83.2185),
    "vadodara": (22.3072, 73.1812),
    "agra": (27.1767, 78.0081),
    "coastal": (13.0827, 80.2707),   # default coastal → Chennai
    "river": (25.5941, 85.1376),     # default river → Patna (Ganga)
    "flood": (22.5726, 88.3639),     # default flood → Kolkata
    "high": (28.6139, 77.2090),      # default high-risk → Delhi
}

_DEFAULT_COORDS = (20.5937, 78.9629)   # Geographic centre of India
_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
_REQUEST_TIMEOUT = 10  # seconds


def _resolve_coords(zone_id: str) -> tuple[float, float]:
    """Return (lat, lon) for a zone_id using zone hierarchy first."""
    zone_coords = zone_coordinates_for(zone_id)
    if zone_coords is not None:
        return zone_coords

    z = zone_id.lower()
    for key, coords in _ZONE_COORDS.items():
        if key in z:
            return coords
    return _DEFAULT_COORDS


def _fetch_open_meteo(lat: float, lon: float) -> dict:
    """
    Call Open-Meteo and return current weather + hourly rain for the
    current hour for the given location in India.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,weathercode",
        "hourly": "precipitation",
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }
    resp = requests.get(_OPEN_METEO_BASE, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_rainfall(zone_id: str) -> dict:
    """
    Return live rainfall data from Open-Meteo for an Indian zone.
    Aggregates the current hour's precipitation (mm) and reports it
    as mm/hr.

    Returns:
    {
      "zone_id": str,
      "rainfall_mm_per_hr": float,
      "duration_hours": float,
      "event_started_at": datetime,
      "event_ended_at": datetime,
      "source": "IMD_OPENMETEO",
      "timestamp": datetime
    }
    """
    lat, lon = _resolve_coords(zone_id)
    now = datetime.now(timezone.utc)
    event_duration_hours = 1.0
    event_start = now - timedelta(hours=event_duration_hours)

    try:
        data = _fetch_open_meteo(lat, lon)
        # current.precipitation is mm in the last hour — directly usable as mm/hr
        current = data.get("current", {})
        rainfall_mm = float(current.get("precipitation", 0.0))

        return {
            "zone_id": zone_id,
            "rainfall_mm_per_hr": round(rainfall_mm, 2),
            "duration_hours": event_duration_hours,
            "event_started_at": event_start,
            "event_ended_at": now,
            "source": "IMD_OPENMETEO",
            "timestamp": now,
        }

    except requests.RequestException as exc:
        logger.error("Open-Meteo rainfall request failed for zone %s: %s", zone_id, exc)
    except (KeyError, ValueError, TypeError) as exc:
        logger.error("Open-Meteo rainfall parse error for zone %s: %s", zone_id, exc)

    logger.warning("Using mock rainfall data for zone %s.", zone_id)
    return {
        "zone_id": zone_id,
        "rainfall_mm_per_hr": 0.0,
        "duration_hours": event_duration_hours,
        "event_started_at": event_start,
        "event_ended_at": now,
        "source": "IMD_OPENMETEO",
        "timestamp": now,
        "error": "API call failed",
    }


def get_temperature(zone_id: str) -> dict:
    """
    Return live temperature and weather condition from Open-Meteo
    for an Indian zone.

    WMO weather code is mapped to GigShield condition labels.

    Returns:
    {
      "zone_id": str,
      "temperature_celsius": float,
      "condition": str,
        ("clear"/"rain"/"heavy_rain"/"flood")
      "source": "IMD_OPENMETEO",
      "timestamp": datetime
    }
    """
    lat, lon = _resolve_coords(zone_id)
    now = datetime.now(timezone.utc)

    try:
        data = _fetch_open_meteo(lat, lon)
        current = data.get("current", {})

        temp = float(current.get("temperature_2m", 30.0))
        precipitation = float(current.get("precipitation", 0.0))
        weathercode = int(current.get("weathercode", 0))

        # Map WMO weather codes + precipitation to GigShield condition labels
        # WMO codes: 0-2 clear, 3 partly cloudy, 51-67 drizzle/rain,
        # 71-77 snow, 80-82 showers, 95-99 thunderstorm
        if precipitation > 100 or weathercode in range(95, 100):
            condition = "flood"
        elif precipitation > 65 or weathercode in {82, 81, 80}:
            condition = "heavy_rain"
        elif precipitation > 20 or weathercode in range(51, 82):
            condition = "rain"
        else:
            condition = "clear"

        return {
            "zone_id": zone_id,
            "temperature_celsius": round(temp, 1),
            "condition": condition,
            "source": "IMD_OPENMETEO",
            "timestamp": now,
        }

    except requests.RequestException as exc:
        logger.error("Open-Meteo temperature request failed for zone %s: %s", zone_id, exc)
    except (KeyError, ValueError, TypeError) as exc:
        logger.error("Open-Meteo temperature parse error for zone %s: %s", zone_id, exc)

    logger.warning("Using mock temperature data for zone %s.", zone_id)
    return {
        "zone_id": zone_id,
        "temperature_celsius": 30.0,
        "condition": "clear",
        "source": "IMD_OPENMETEO",
        "timestamp": now,
        "error": "API call failed",
    }
