"""Mock API exports."""

from mock_apis.aqi_mock import get_aqi
from mock_apis.curfew_mock import get_curfew_status
from mock_apis.flood_mock import get_flood_alert
from mock_apis.fraud_signal_mock import (
	get_cell_tower_signal,
	get_gps_signal,
	get_ip_geolocation_signal,
	get_motion_signal,
	get_order_activity_signal,
)
from mock_apis.platform_mock import get_platform_status
from mock_apis.weather_mock import get_rainfall, get_temperature

__all__ = [
	"get_rainfall",
	"get_temperature",
	"get_aqi",
	"get_flood_alert",
	"get_curfew_status",
	"get_platform_status",
	"get_gps_signal",
	"get_cell_tower_signal",
	"get_ip_geolocation_signal",
	"get_motion_signal",
	"get_order_activity_signal",
]
