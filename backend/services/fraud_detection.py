"""Fraud detection service functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from mock_apis import (
   get_aqi,
   get_cell_tower_signal,
   get_curfew_status,
   get_flood_alert,
   get_gps_signal,
   get_ip_geolocation_signal,
   get_motion_signal,
   get_order_activity_signal,
   get_platform_status,
   get_rainfall,
   get_temperature,
)
from models.claim import Claim
from models.disruption import Disruption
from models.worker import Worker


def get_zone_disruption_snapshot(zone_id: str) -> dict:
   """Aggregate mock trigger APIs into a disruption context snapshot."""
   rainfall = get_rainfall(zone_id)
   aqi = get_aqi(zone_id)
   flood = get_flood_alert(zone_id)
   curfew = get_curfew_status(zone_id)
   platform = get_platform_status(zone_id)
   temperature = get_temperature(zone_id)

   severity_candidates: list[float] = []
   active_sources: list[str] = []

   rainfall_mm = float(rainfall["rainfall_mm_per_hr"])
   if rainfall_mm > 50.0:
      severity_candidates.append(min(rainfall_mm / 100.0, 1.0))
      active_sources.append(rainfall.get("source", "IMD_MOCK"))

   aqi_value = int(aqi["aqi"])
   if aqi_value > 300:
      severity_candidates.append(min((aqi_value - 300) / 200.0, 1.0))
      active_sources.append(aqi.get("source", "CPCB_MOCK"))

   if bool(flood["alert_active"]):
      flood_severity = {"watch": 0.6, "warning": 0.85, "emergency": 0.95}.get(flood["alert_level"], 0.85)
      severity_candidates.append(flood_severity)
      active_sources.append(flood.get("source", "NDMA_MOCK"))

   if bool(curfew["curfew_active"]):
      curfew_severity = 0.55 if curfew["curfew_level"] == "night" else 0.9
      severity_candidates.append(curfew_severity)
      active_sources.append(curfew.get("source", "CIVIC_CURFEW_MOCK"))

   if bool(platform["outage_active"]):
      platform_severity = max(
         min(float(platform["api_error_rate"]) / 0.35, 1.0),
         min((100.0 - float(platform["uptime_percent"])) / 10.0, 1.0),
      )
      severity_candidates.append(platform_severity)
      active_sources.append(platform.get("source", "PLATFORM_HEALTH_MOCK"))

   temp = float(temperature["temperature_celsius"])
   if temp >= 42.0 or temp <= 5.0:
      severity_candidates.append(min(abs(temp - 30.0) / 20.0, 1.0))
      active_sources.append(temperature.get("source", "IMD_MOCK"))

   severity_index = round(max(severity_candidates) if severity_candidates else 0.0, 3)

   return {
      "zone_id": zone_id,
      "active_trigger_count": len(severity_candidates),
      "severity_index": severity_index,
      "sources": sorted(set(active_sources)),
      "timestamp": datetime.now(timezone.utc),
   }


def build_claim_metadata(worker: Worker, claimed_zone_id: str) -> dict:
   """Build spoofing metadata from mock telemetry APIs."""
   worker_id = str(worker.id)
   disruption_context = get_zone_disruption_snapshot(claimed_zone_id)
   severity_index = float(disruption_context["severity_index"])

   gps_signal = get_gps_signal(worker_id=worker_id, claimed_zone_id=claimed_zone_id, home_zone_id=worker.micro_zone_id)
   cell_signal = get_cell_tower_signal(worker_id=worker_id, claimed_zone_id=claimed_zone_id)
   ip_signal = get_ip_geolocation_signal(worker_id=worker_id, claimed_zone_id=claimed_zone_id)
   motion_signal = get_motion_signal(worker_id=worker_id, claimed_zone_id=claimed_zone_id)
   activity_signal = get_order_activity_signal(
      worker_id=worker_id,
      claimed_zone_id=claimed_zone_id,
      disruption_severity=severity_index,
   )

   return {
      "gps_zone": gps_signal["gps_zone"],
      "gps_confidence": gps_signal["gps_confidence"],
      "cell_tower_zone": cell_signal["cell_tower_zone"],
      "ip_zone": ip_signal["ip_zone"],
      "is_stationary": motion_signal["is_stationary"],
      "acceptance_rate_during": activity_signal["acceptance_rate_during"],
      "online_hours_during": activity_signal["online_hours_during"],
      "claim_timestamp": datetime.now(timezone.utc),
      "disruption_context": disruption_context,
   }


def _evaluate_route_history(worker: Worker, claimed_zone_id: str, db: Session | None) -> bool:
   if db is None:
      return claimed_zone_id == worker.micro_zone_id

   count = (
      db.query(Claim)
      .join(Disruption, Disruption.id == Claim.disruption_id)
      .filter(Claim.worker_id == worker.id, Disruption.zone_id == claimed_zone_id)
      .count()
   )
   return count > 0


def _evaluate_cluster_flag(claimed_zone_id: str, claim_time: datetime, db: Session | None) -> tuple[bool, float, int]:
   if db is None:
      return False, 1.0, 0

   one_hour_ago = claim_time - timedelta(hours=1)
   seven_days_ago = claim_time - timedelta(days=7)

   recent_count = (
      db.query(Claim)
      .join(Disruption, Disruption.id == Claim.disruption_id)
      .filter(
         Disruption.zone_id == claimed_zone_id,
         Claim.created_at >= one_hour_ago,
         Claim.created_at <= claim_time,
      )
      .count()
   )

   historical_count = (
      db.query(Claim)
      .join(Disruption, Disruption.id == Claim.disruption_id)
      .filter(
         Disruption.zone_id == claimed_zone_id,
         Claim.created_at >= seven_days_ago,
         Claim.created_at < one_hour_ago,
      )
      .count()
   )

   historical_hours = max(int((one_hour_ago - seven_days_ago).total_seconds() // 3600), 1)
   historical_avg_per_hour = max(historical_count / historical_hours, 0.5)
   syndicate_flag = recent_count > (3.0 * historical_avg_per_hour)

   return syndicate_flag, round(historical_avg_per_hour, 3), recent_count


def run_spoofing_check(worker: Worker, claimed_zone_id: str, claim_metadata: dict, db: Session | None = None) -> dict:
   """Run 7-signal spoofing detection and return decision details."""
   claim_time = claim_metadata.get("claim_timestamp")
   if not isinstance(claim_time, datetime):
      claim_time = datetime.now(timezone.utc)

   gps_confidence = float(claim_metadata.get("gps_confidence", 0.0))
   gps_zone = str(claim_metadata.get("gps_zone", worker.micro_zone_id))
   cell_tower_zone = str(claim_metadata.get("cell_tower_zone", ""))
   ip_zone = str(claim_metadata.get("ip_zone", ""))
   is_stationary = bool(claim_metadata.get("is_stationary", True))
   acceptance_rate = float(claim_metadata.get("acceptance_rate_during", 0.0))

   gps_match = gps_confidence > 0.75 or gps_zone == claimed_zone_id
   cell_match = cell_tower_zone == claimed_zone_id
   accel_match = not is_stationary
   ip_match = ip_zone == claimed_zone_id
   route_history_match = _evaluate_route_history(worker=worker, claimed_zone_id=claimed_zone_id, db=db)
   acceptance_match = acceptance_rate > 0.3
   syndicate_flag, historical_avg, recent_count = _evaluate_cluster_flag(
      claimed_zone_id=claimed_zone_id,
      claim_time=claim_time,
      db=db,
   )
   cluster_match = not syndicate_flag

   signal_results = {
      "gps_match": gps_match,
      "cell_tower_match": cell_match,
      "accelerometer_motion": accel_match,
      "ip_geolocation_match": ip_match,
      "route_history_match": route_history_match,
      "order_acceptance_match": acceptance_match,
      "cluster_detection_match": cluster_match,
   }

   failed_signals = [name for name, passed in signal_results.items() if not passed]
   spoofing_signals_fired = len(failed_signals)

   if spoofing_signals_fired >= 3:
      baf_modifier = 0.0
   elif spoofing_signals_fired == 2:
      baf_modifier = 0.85
   else:
      baf_modifier = 1.0

   return {
      "spoofing_signals_fired": spoofing_signals_fired,
      "syndicate_flag": syndicate_flag,
      "audit_required": spoofing_signals_fired >= 2 or syndicate_flag,
      "baf_modifier": baf_modifier,
      "failed_signals": failed_signals,
      "signals_detail": {
         **signal_results,
         "gps_confidence": gps_confidence,
         "acceptance_rate_during": acceptance_rate,
         "cluster_recent_count": recent_count,
         "cluster_historical_avg_per_hour": historical_avg,
      },
   }
