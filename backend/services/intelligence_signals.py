"""Extra zone intelligence signals for hackathon-grade forecasting and simulation."""

from __future__ import annotations

import logging
import math
import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus

import httpx
import requests

from config import settings
from services.zone_granularity import parent_zone_for, zone_coordinates_for

logger = logging.getLogger(__name__)

_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
_NAGER_HOLIDAY_BASE = "https://date.nager.at/api/v3/PublicHolidays"
_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
_EONET_BASE = "https://eonet.gsfc.nasa.gov/api/v3/events"
_REQUEST_TIMEOUT = 8

_ZONE_CITY_HINTS = {
    "BLR_KORAMANGALA_004": "Bengaluru",
    "PUN_KOTHRUD_002": "Pune",
    "HYD_GACHIBOWLI_007": "Hyderabad",
}


def _zone_city(zone_id: str) -> str:
    parent_zone_id = parent_zone_for(zone_id)
    if parent_zone_id in _ZONE_CITY_HINTS:
        return _ZONE_CITY_HINTS[parent_zone_id]

    lowered = zone_id.lower()
    for key, value in {
        "bengaluru": "Bengaluru",
        "bangalore": "Bengaluru",
        "pune": "Pune",
        "hyderabad": "Hyderabad",
        "mumbai": "Mumbai",
        "delhi": "Delhi",
        "chennai": "Chennai",
        "kolkata": "Kolkata",
    }.items():
        if key in lowered:
            return value
    return parent_zone_id.replace("_", " ").title()


def _geo_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    return 2.0 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


@lru_cache(maxsize=8)
def _holiday_dates(year: int) -> set[date]:
    try:
        response = requests.get(f"{_NAGER_HOLIDAY_BASE}/{year}/IN", timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        holidays = response.json()
        return {datetime.fromisoformat(item["date"]).date() for item in holidays if item.get("date")}
    except Exception:
        return set()


def _fetch_weather_forecast(zone_id: str, forecast_date: date) -> dict[str, Any]:
    coords = zone_coordinates_for(zone_id) or (20.5937, 78.9629)
    params = {
        "latitude": coords[0],
        "longitude": coords[1],
        "daily": "precipitation_sum,windspeed_10m_max,weathercode,temperature_2m_max",
        "forecast_days": 7,
        "timezone": "Asia/Kolkata",
    }
    try:
        response = requests.get(_OPEN_METEO_BASE, params=params, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        daily = payload.get("daily", {})
        dates = [datetime.fromisoformat(item).date() for item in daily.get("time", [])]
        if forecast_date in dates:
            index = dates.index(forecast_date)
            return {
                "precipitation_sum_mm": float((daily.get("precipitation_sum") or [0.0])[index] or 0.0),
                "windspeed_10m_max_kph": float((daily.get("windspeed_10m_max") or [0.0])[index] or 0.0),
                "weathercode": int((daily.get("weathercode") or [0])[index] or 0),
                "temperature_max_celsius": float((daily.get("temperature_2m_max") or [0.0])[index] or 0.0),
            }
    except Exception:
        logger.warning("Using mock weather forecast for zone %s because the live weather API failed.", zone_id)
        pass

    return {
        "precipitation_sum_mm": 0.0,
        "windspeed_10m_max_kph": 0.0,
        "weathercode": 0,
        "temperature_max_celsius": 30.0,
    }


def _traffic_anchor_points(zone_id: str) -> tuple[tuple[float, float], tuple[float, float]]:
    coords = zone_coordinates_for(zone_id) or (20.5937, 78.9629)
    lat, lon = coords
    destination = (lat + 0.035, lon + 0.025)
    return coords, destination


def _traffic_from_tomtom(zone_id: str) -> dict[str, Any] | None:
    if not settings.tomtom_traffic_api_key:
        return None
    coords, _ = _traffic_anchor_points(zone_id)
    url = f"{settings.tomtom_traffic_base_url.rstrip('/')}/flowSegmentData/absolute/10/json"
    params = {
        "point": f"{coords[0]},{coords[1]}",
        "key": settings.tomtom_traffic_api_key,
    }
    try:
        response = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json().get("flowSegmentData", {})
        current_speed = float(payload.get("currentSpeed", 0.0) or 0.0)
        free_flow_speed = float(payload.get("freeFlowSpeed", 0.0) or 0.0)
        current_travel_time = float(payload.get("currentTravelTime", 0.0) or 0.0)
        free_flow_travel_time = float(payload.get("freeFlowTravelTime", 0.0) or 0.0)
        delay_seconds = max(current_travel_time - free_flow_travel_time, 0.0)
        ratio = 1.0 - (current_speed / free_flow_speed) if free_flow_speed > 0 else 0.0
        return {
            "provider": "tomtom",
            "traffic_delay_minutes": round(delay_seconds / 60.0, 2),
            "traffic_jam_factor": round(max(ratio, 0.0), 3),
            "traffic_confidence": round(float(payload.get("confidence", 0.0) or 0.0) / 100.0, 3),
            "traffic_incident_count": 1 if bool(payload.get("roadClosure", False)) else 0,
            "traffic_speed_kph": round(current_speed, 2),
            "traffic_free_flow_speed_kph": round(free_flow_speed, 2),
            "traffic_risk": round(min(max(ratio, 0.0) * 0.85 + min(delay_seconds / 1800.0, 1.0) * 0.15, 1.0), 3),
        }
    except Exception:
        return None


def _traffic_from_google_routes(zone_id: str) -> dict[str, Any] | None:
    if not settings.google_routes_api_key:
        return None
    origin, destination = _traffic_anchor_points(zone_id)
    url = f"{settings.google_routes_base_url.rstrip('/')}/routes"
    payload = {
        "origin": {"location": {"latLng": {"latitude": origin[0], "longitude": origin[1]}}},
        "destination": {"location": {"latLng": {"latitude": destination[0], "longitude": destination[1]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        "computeAlternativeRoutes": False,
        "languageCode": "en-IN",
        "units": "METRIC",
        "departureTime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_routes_api_key,
        "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters,routes.travelAdvisory.delayDuration,routes.travelAdvisory.speedReadingIntervals",
    }
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        route = (data.get("routes") or [{}])[0]
        advisory = route.get("travelAdvisory", {}) or {}
        duration = route.get("duration", "PT0S")
        static_duration = route.get("staticDuration", "PT0S")
        delay_duration = advisory.get("delayDuration", "PT0S")

        def _iso_to_seconds(value: str | None) -> float:
            if not value:
                return 0.0
            total = 0.0
            fragment = value.replace("PT", "")
            number = ""
            for char in fragment:
                if char.isdigit() or char == ".":
                    number += char
                    continue
                if char == "H" and number:
                    total += float(number) * 3600.0
                elif char == "M" and number:
                    total += float(number) * 60.0
                elif char == "S" and number:
                    total += float(number)
                number = ""
            return total

        duration_seconds = _iso_to_seconds(duration)
        static_seconds = _iso_to_seconds(static_duration)
        delay_seconds = _iso_to_seconds(delay_duration)
        intervals = advisory.get("speedReadingIntervals") or []
        slow_ratio = 0.0
        if intervals:
            slow_ratio = sum(1 for item in intervals if str(item.get("speed", "")).lower() in {"slow", "slower", "traffic_jam"}) / len(intervals)
        traffic_risk = min(max((delay_seconds / max(static_seconds, 1.0)) * 0.75 + slow_ratio * 0.25, 0.0), 1.0)
        return {
            "provider": "google_routes",
            "traffic_delay_minutes": round(delay_seconds / 60.0, 2),
            "traffic_jam_factor": round(slow_ratio, 3),
            "traffic_confidence": 0.72,
            "traffic_incident_count": len(intervals),
            "traffic_speed_kph": round(float(route.get("distanceMeters", 0.0) or 0.0) / max(duration_seconds / 3600.0, 1 / 60.0) / 1000.0, 2) if duration_seconds > 0 else 0.0,
            "traffic_free_flow_speed_kph": round(float(route.get("distanceMeters", 0.0) or 0.0) / max(static_seconds / 3600.0, 1 / 60.0) / 1000.0, 2) if static_seconds > 0 else 0.0,
            "traffic_risk": round(traffic_risk, 3),
        }
    except Exception:
        return None


def _traffic_from_here(zone_id: str) -> dict[str, Any] | None:
    if not settings.here_traffic_api_key:
        return None
    origin, destination = _traffic_anchor_points(zone_id)
    url = f"{settings.here_traffic_base_url.rstrip('/')}/routes"
    params = {
        "transportMode": "car",
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "return": "summary,polyline,actions",
        "traffic[mode]": "enabled",
        "apikey": settings.here_traffic_api_key,
    }
    try:
        response = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        route = (data.get("routes") or [{}])[0]
        section = (route.get("sections") or [{}])[0]
        summary = section.get("summary", {}) or {}
        traffic_time = float(summary.get("trafficTime", 0.0) or 0.0)
        base_time = float(summary.get("baseDuration", 0.0) or 0.0)
        duration = float(summary.get("duration", 0.0) or 0.0)
        delay_seconds = max(traffic_time - base_time, 0.0)
        risk = min(max((delay_seconds / max(base_time, 1.0)) * 0.8 + min(duration / 3600.0, 1.0) * 0.2, 0.0), 1.0)
        return {
            "provider": "here",
            "traffic_delay_minutes": round(delay_seconds / 60.0, 2),
            "traffic_jam_factor": round(min(max((traffic_time - base_time) / max(base_time, 1.0), 0.0), 1.0), 3),
            "traffic_confidence": round(float(summary.get("confidence", 0.7) or 0.7), 3),
            "traffic_incident_count": int(len(section.get("transport", []) or [])),
            "traffic_speed_kph": round(float(summary.get("length", 0.0) or 0.0) / max(duration / 3600.0, 1 / 60.0) / 1000.0, 2) if duration > 0 else 0.0,
            "traffic_free_flow_speed_kph": round(float(summary.get("length", 0.0) or 0.0) / max(base_time / 3600.0, 1 / 60.0) / 1000.0, 2) if base_time > 0 else 0.0,
            "traffic_risk": round(risk, 3),
        }
    except Exception:
        return None


def _fetch_traffic_signal(zone_id: str) -> dict[str, Any]:
    provider_order = [settings.traffic_provider, "google_routes", "tomtom", "here"]
    provider_order = list(dict.fromkeys(item for item in provider_order if item and item != "auto"))
    attempts = []
    for provider in provider_order:
        attempts.append(provider)
        if provider == "google_routes":
            result = _traffic_from_google_routes(zone_id)
        elif provider == "tomtom":
            result = _traffic_from_tomtom(zone_id)
        elif provider == "here":
            result = _traffic_from_here(zone_id)
        else:
            result = None
        if result:
            result["attempted_providers"] = attempts
            return result

    coords = zone_coordinates_for(zone_id) or (20.5937, 78.9629)
    _, destination = _traffic_anchor_points(zone_id)
    distance_km = _geo_distance_km(coords[0], coords[1], destination[0], destination[1])
    risk = min(distance_km / 12.0, 1.0)
    logger.warning("Using mock traffic values for zone %s because all traffic providers failed.", zone_id)
    return {
        "provider": "heuristic",
        "traffic_delay_minutes": round(distance_km * 1.8, 2),
        "traffic_jam_factor": round(risk * 0.6, 3),
        "traffic_confidence": 0.28,
        "traffic_incident_count": 0,
        "traffic_speed_kph": round(max(18.0, 42.0 - distance_km * 1.5), 2),
        "traffic_free_flow_speed_kph": 42.0,
        "traffic_risk": round(risk, 3),
        "attempted_providers": attempts or ["heuristic"],
    }


def _classify_news_headlines(zone_id: str, titles: list[str]) -> dict[str, Any]:
    text_blob = " ".join(titles).lower()
    keyword_rules: list[tuple[str, str, float, list[str]]] = [
        ("flood", "flood", 0.94, ["flood", "waterlogging", "rain", "storm", "monsoon"]),
        ("traffic", "traffic", 0.88, ["traffic", "jam", "road", "route", "delay", "accident", "collision"]),
        ("curfew", "curfew", 0.86, ["curfew", "lockdown", "shutdown", "restriction"]),
        ("strike", "industrial_action", 0.84, ["strike", "protest", "union", "walkout"]),
        ("festival", "crowd_event", 0.82, ["festival", "procession", "rally", "concert", "match"]),
        ("fire", "fire", 0.9, ["fire", "blaze", "smoke", "wildfire"]),
        ("security", "security", 0.78, ["blast", "attack", "security", "threat", "raid"]),
        ("platform", "platform_outage", 0.76, ["outage", "downtime", "service", "outage", "failure"]),
    ]
    for keyword, label, confidence, tokens in keyword_rules:
        if any(token in text_blob for token in tokens):
            return {
                "disruption_type": label,
                "confidence": confidence,
                "source": "heuristic",
                "matched_keyword": keyword,
            }

    if settings.news_llm_enabled and settings.news_llm_api_key:
        prompt = {
            "zone_id": zone_id,
            "task": "Classify RSS/news headlines into one disruption label from flood, traffic, curfew, strike, festival, fire, security, platform_outage, general.",
            "headlines": titles[:8],
            "output_format": {"disruption_type": "string", "confidence": "number 0-1", "reason": "string"},
        }
        body = {
            "model": settings.news_llm_model,
            "messages": [
                {"role": "system", "content": "Return only compact JSON with disruption_type, confidence, and reason."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            "temperature": 0.1,
        }
        try:
            with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                resp = client.post(
                    settings.news_llm_endpoint,
                    headers={
                        "Authorization": f"Bearer {settings.news_llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
                payload = resp.json()
                text = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                if text:
                    parsed = json.loads(text)
                    label = str(parsed.get("disruption_type", "general")).strip().lower()
                    if not label:
                        label = "general"
                    return {
                        "disruption_type": label,
                        "confidence": float(parsed.get("confidence", 0.62) or 0.62),
                        "source": settings.news_llm_model,
                        "reason": str(parsed.get("reason", "LLM classification")),
                    }
        except Exception:
            pass

    if settings.news_llm_enabled:
        logger.warning("Using heuristic news classification for zone %s because the news LLM was unavailable.", zone_id)
    logger.warning("Using mock news classification for zone %s because no strong keyword or LLM signal was available.", zone_id)
    return {"disruption_type": "general", "confidence": 0.35, "source": "fallback", "reason": "No strong keyword or model signal"}


def _fetch_news_signal(zone_id: str) -> dict[str, Any]:
    city = _zone_city(zone_id)
    query = quote_plus(f'{city} disruption OR traffic OR rally OR festival OR storm')
    url = f"{_GOOGLE_NEWS_RSS}?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(url, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        items = root.findall(".//item")[:8]
        titles = [(item.findtext("title") or "") for item in items]
        classification = _classify_news_headlines(zone_id=zone_id, titles=titles)
        text_blob = " ".join(title.lower() for title in titles)
        score = 0.0
        for token, weight in {
            "traffic": 0.12,
            "accident": 0.18,
            "flood": 0.26,
            "storm": 0.22,
            "festival": 0.20,
            "rally": 0.20,
            "election": 0.25,
            "strike": 0.24,
            "protest": 0.18,
            "shutdown": 0.15,
        }.items():
            if token in text_blob:
                score += weight
        score += min(len(items) / 12.0, 0.35)
        classification_score = float(classification.get("confidence", 0.0))
        news_risk = min(max(score, classification_score), 1.0)
        return {
            "news_headline_count": len(items),
            "news_risk": news_risk,
            "news_classification": classification,
            "source": "google_news_rss",
        }
    except Exception:
        logger.warning("Using mock news signal for zone %s because Google News RSS failed.", zone_id)
        return {
            "news_headline_count": 0,
            "news_risk": 0.0,
            "news_classification": {"disruption_type": "general", "confidence": 0.0, "source": "google_news_rss"},
            "source": "google_news_rss",
        }


def _fetch_eonet_fire_risk(zone_id: str) -> dict[str, Any]:
    coords = zone_coordinates_for(zone_id) or (20.5937, 78.9629)
    try:
        response = requests.get(f"{_EONET_BASE}?category=wildfires&status=open", timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        events = payload.get("events", [])
        nearby = 0
        for event in events[:40]:
            for geometry in event.get("geometry", []):
                lat = geometry.get("coordinates", [None, None])[1]
                lon = geometry.get("coordinates", [None, None])[0]
                if lat is None or lon is None:
                    continue
                if _geo_distance_km(coords[0], coords[1], float(lat), float(lon)) <= 350.0:
                    nearby += 1
                    break
        return {"fire_event_count": nearby, "fire_risk": min(nearby / 4.0, 1.0), "source": "nasa_eonet"}
    except Exception:
        logger.warning("Using mock fire signal for zone %s because EONET failed.", zone_id)
        return {"fire_event_count": 0, "fire_risk": 0.0, "source": "nasa_eonet"}


def get_zone_intelligence_snapshot(zone_id: str, forecast_date: date | None = None) -> dict[str, Any]:
    target_date = forecast_date or datetime.now(timezone.utc).date()
    weather = _fetch_weather_forecast(zone_id=zone_id, forecast_date=target_date)
    holiday = target_date in _holiday_dates(target_date.year)
    news = _fetch_news_signal(zone_id)
    fire = _fetch_eonet_fire_risk(zone_id)
    traffic = _fetch_traffic_signal(zone_id)

    wind_speed = float(weather.get("windspeed_10m_max_kph", 0.0))
    precipitation = float(weather.get("precipitation_sum_mm", 0.0))
    weathercode = int(weather.get("weathercode", 0))
    thunderstorm_risk = 1.0 if weathercode >= 95 else 0.0
    wind_risk = min(wind_speed / 70.0, 1.0)
    rain_risk = min(precipitation / 80.0, 1.0)
    holiday_risk = 0.18 if holiday else 0.0
    road_delay_risk = min(max(float(traffic.get("traffic_risk", 0.0)), (rain_risk * 0.45) + (news["news_risk"] * 0.30) + (wind_risk * 0.25)), 1.0)

    signal_pressure = min(
        (0.28 * rain_risk)
        + (0.18 * wind_risk)
        + (0.18 * thunderstorm_risk)
        + (0.12 * holiday_risk)
        + (0.12 * news["news_risk"])
        + (0.08 * fire["fire_risk"])
        + (0.04 * float(traffic.get("traffic_risk", 0.0))),
        1.0,
    )

    return {
        "zone_id": zone_id,
        "parent_zone_id": parent_zone_for(zone_id),
        "city": _zone_city(zone_id),
        "forecast_date": target_date.isoformat(),
        "holiday_active": holiday,
        "precipitation_sum_mm": round(precipitation, 2),
        "windspeed_10m_max_kph": round(wind_speed, 2),
        "weathercode": weathercode,
        "thunderstorm_risk": round(thunderstorm_risk, 3),
        "news_headline_count": int(news["news_headline_count"]),
        "news_risk": round(float(news["news_risk"]), 3),
        "news_classification": news.get("news_classification", {"disruption_type": "general", "confidence": 0.0, "source": "google_news_rss"}),
        "fire_event_count": int(fire["fire_event_count"]),
        "fire_risk": round(float(fire["fire_risk"]), 3),
        "traffic_provider": traffic.get("provider", "heuristic"),
        "traffic_delay_minutes": float(traffic.get("traffic_delay_minutes", 0.0)),
        "traffic_jam_factor": float(traffic.get("traffic_jam_factor", 0.0)),
        "traffic_confidence": float(traffic.get("traffic_confidence", 0.0)),
        "traffic_incident_count": int(traffic.get("traffic_incident_count", 0)),
        "traffic_speed_kph": float(traffic.get("traffic_speed_kph", 0.0)),
        "traffic_free_flow_speed_kph": float(traffic.get("traffic_free_flow_speed_kph", 0.0)),
        "traffic_risk": round(float(traffic.get("traffic_risk", 0.0)), 3),
        "road_delay_risk": round(road_delay_risk, 3),
        "signal_pressure": round(signal_pressure, 3),
        "sources": [weather.get("source", "open_meteo"), news.get("source", "google_news_rss"), fire.get("source", "nasa_eonet"), traffic.get("provider", "heuristic")],
    }


def get_zone_intelligence_series(zone_id: str, days: int = 7) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    return [get_zone_intelligence_snapshot(zone_id=zone_id, forecast_date=today + timedelta(days=offset)) for offset in range(days)]
