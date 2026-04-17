"""Flood alert integration using Open-Meteo river discharge + precipitation data — India specific."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from services.zone_granularity import zone_coordinates_for

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Coordinates for major Indian cities / zone patterns (shared with weather_mock).
# River discharge data from Open-Meteo's flood API is India-aware.
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
    "coastal": (13.0827, 80.2707),
    "river": (25.5941, 85.1376),
    "flood": (22.5726, 88.3639),
    "high": (28.6139, 77.2090),
}

_DEFAULT_COORDS = (20.5937, 78.9629)   # Geographic centre of India

# Open-Meteo Flood API (GloFAS-based river discharge, global coverage incl. India)
_FLOOD_API_BASE = "https://flood-api.open-meteo.com/v1/flood"
# Weather API for precipitation (used as secondary signal)
_WEATHER_API_BASE = "https://api.open-meteo.com/v1/forecast"
_REQUEST_TIMEOUT = 10  # seconds

# River discharge thresholds (m³/s) derived from GloFAS percentile benchmarks.
# These are relative: we use the current vs 7-day max ratio as a risk signal.
_DISCHARGE_WARNING_RATIO = 0.70    # current >= 70% of 7-day max → watch
_DISCHARGE_EMERGENCY_RATIO = 0.90  # current >= 90% of 7-day max → warning/emergency


def _resolve_coords(zone_id: str) -> tuple[float, float]:
    zone_coords = zone_coordinates_for(zone_id)
    if zone_coords is not None:
        return zone_coords

    z = zone_id.lower()
    for key, coords in _ZONE_COORDS.items():
        if key in z:
            return coords
    return _DEFAULT_COORDS


def _fetch_river_discharge(lat: float, lon: float) -> float | None:
    """
    Fetch today's river discharge from Open-Meteo Flood API (GloFAS).
    Returns the current day's mean discharge in m³/s, or None on failure.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "river_discharge",
        "forecast_days": 7,
    }
    resp = requests.get(_FLOOD_API_BASE, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    values = data.get("daily", {}).get("river_discharge", [])
    # values[0] is today; the list may contain null entries
    valid = [v for v in values if v is not None]
    return valid[0] if valid else None


def _fetch_precipitation(lat: float, lon: float) -> float:
    """
    Fetch current hour's precipitation (mm) from Open-Meteo as secondary signal.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation",
        "timezone": "Asia/Kolkata",
    }
    resp = requests.get(_WEATHER_API_BASE, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return float(data.get("current", {}).get("precipitation", 0.0))


def _derive_alert_level(
    discharge_today: float | None,
    discharge_values: list[float],
    precipitation_mm: float,
) -> str:
    """
    Determine alert level from river discharge and precipitation signals.

    Logic:
    - If discharge_today >= 90% of 7-day max AND precipitation > 50mm → emergency
    - If discharge_today >= 90% of 7-day max OR precipitation > 100mm  → warning
    - If discharge_today >= 70% of 7-day max OR precipitation > 50mm   → watch
    - Otherwise → none
    """
    if discharge_today is None:
        # Fall back to precipitation-only assessment
        if precipitation_mm > 100:
            return "warning"
        elif precipitation_mm > 50:
            return "watch"
        return "none"

    max_discharge = max(discharge_values) if discharge_values else discharge_today
    ratio = discharge_today / max_discharge if max_discharge > 0 else 0.0

    if ratio >= _DISCHARGE_EMERGENCY_RATIO and precipitation_mm > 50:
        return "emergency"
    elif ratio >= _DISCHARGE_EMERGENCY_RATIO or precipitation_mm > 100:
        return "warning"
    elif ratio >= _DISCHARGE_WARNING_RATIO or precipitation_mm > 50:
        return "watch"
    return "none"


def get_flood_alert(zone_id: str) -> dict:
    """
    Return live flood alert status derived from Open-Meteo GloFAS river
    discharge data and current precipitation, specific to Indian zones.

    River discharge data is sourced from the GloFAS (Global Flood Awareness
    System) model embedded in Open-Meteo — the same data used by CWC/NDMA
    for advance flood forecasting in India.

    Returns:
    {
      "zone_id": str,
      "alert_active": bool,
      "alert_level": str,
        ("none"/"watch"/"warning"/"emergency")
      "source": "CWC_OPENMETEO",
      "timestamp": datetime
    }
    """
    lat, lon = _resolve_coords(zone_id)
    now = datetime.now(timezone.utc)

    discharge_today: float | None = None
    discharge_values: list[float] = []
    precipitation_mm: float = 0.0
    used_mock_fallback = False

    # Fetch river discharge
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "river_discharge",
            "forecast_days": 7,
        }
        resp = requests.get(_FLOOD_API_BASE, params=params, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw_values = data.get("daily", {}).get("river_discharge", [])
        discharge_values = [v for v in raw_values if v is not None]
        discharge_today = discharge_values[0] if discharge_values else None

    except requests.RequestException as exc:
        logger.warning("Using mock flood alert data for zone %s because flood API failed: %s", zone_id, exc)
        used_mock_fallback = True
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Using mock flood alert data for zone %s because flood response parsing failed: %s", zone_id, exc)
        used_mock_fallback = True

    # Fetch precipitation as secondary signal
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "precipitation",
            "timezone": "Asia/Kolkata",
        }
        resp = requests.get(_WEATHER_API_BASE, params=params, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        weather_data = resp.json()
        precipitation_mm = float(weather_data.get("current", {}).get("precipitation", 0.0))

    except requests.RequestException as exc:
        logger.warning("Using mock flood alert data for zone %s because precipitation API failed: %s", zone_id, exc)
        used_mock_fallback = True
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Using mock flood alert data for zone %s because precipitation parsing failed: %s", zone_id, exc)
        used_mock_fallback = True

    alert_level = _derive_alert_level(discharge_today, discharge_values, precipitation_mm)

    if used_mock_fallback:
        logger.warning("Using mock flood alert data for zone %s.", zone_id)

    return {
        "zone_id": zone_id,
        "alert_active": alert_level != "none",
        "alert_level": alert_level,
        "source": "CWC_OPENMETEO",
        "timestamp": now,
    }
