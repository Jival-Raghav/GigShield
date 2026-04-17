"""Fine-grained zone mapping utilities with parent-zone compatibility."""

from __future__ import annotations


_PARENT_ZONE_COORDS: dict[str, tuple[float, float]] = {
    "BLR_KORAMANGALA_004": (12.935, 77.6375),
    "PUN_KOTHRUD_002": (18.51, 73.815),
    "HYD_GACHIBOWLI_007": (17.4425, 78.3725),
}


# Bounding boxes are intentionally medium-sized neighborhood sectors.
_FINE_ZONES: dict[str, dict] = {
    "BLR_KORAMANGALA_NW": {
        "parent_zone_id": "BLR_KORAMANGALA_004",
        "lat": (12.94, 12.955),
        "lng": (77.61, 77.635),
    },
    "BLR_KORAMANGALA_CENTRAL": {
        "parent_zone_id": "BLR_KORAMANGALA_004",
        "lat": (12.925, 12.94),
        "lng": (77.625, 77.65),
    },
    "BLR_KORAMANGALA_SE": {
        "parent_zone_id": "BLR_KORAMANGALA_004",
        "lat": (12.915, 12.93),
        "lng": (77.64, 77.665),
    },
    "PUN_KOTHRUD_W": {
        "parent_zone_id": "PUN_KOTHRUD_002",
        "lat": (18.505, 18.535),
        "lng": (73.785, 73.81),
    },
    "PUN_KOTHRUD_CENTRAL": {
        "parent_zone_id": "PUN_KOTHRUD_002",
        "lat": (18.495, 18.525),
        "lng": (73.805, 73.83),
    },
    "PUN_KOTHRUD_SE": {
        "parent_zone_id": "PUN_KOTHRUD_002",
        "lat": (18.49, 18.515),
        "lng": (73.82, 73.84),
    },
    "HYD_GACHIBOWLI_W": {
        "parent_zone_id": "HYD_GACHIBOWLI_007",
        "lat": (17.44, 17.47),
        "lng": (78.34, 78.365),
    },
    "HYD_GACHIBOWLI_CENTRAL": {
        "parent_zone_id": "HYD_GACHIBOWLI_007",
        "lat": (17.435, 17.46),
        "lng": (78.36, 78.385),
    },
    "HYD_GACHIBOWLI_E": {
        "parent_zone_id": "HYD_GACHIBOWLI_007",
        "lat": (17.43, 17.455),
        "lng": (78.38, 78.405),
    },
}


def parent_zone_for(zone_id: str) -> str:
    if zone_id in _FINE_ZONES:
        return str(_FINE_ZONES[zone_id]["parent_zone_id"])
    return zone_id


def zone_coordinates_for(zone_id: str) -> tuple[float, float] | None:
    if zone_id in _FINE_ZONES:
        lat_min, lat_max = _FINE_ZONES[zone_id]["lat"]
        lng_min, lng_max = _FINE_ZONES[zone_id]["lng"]
        return ((lat_min + lat_max) / 2.0, (lng_min + lng_max) / 2.0)

    parent_zone_id = parent_zone_for(zone_id)
    if parent_zone_id in _PARENT_ZONE_COORDS:
        return _PARENT_ZONE_COORDS[parent_zone_id]

    return None


def map_coordinates_to_zone(latitude: float | None, longitude: float | None) -> dict | None:
    if latitude is None or longitude is None:
        return None

    for fine_zone_id, data in _FINE_ZONES.items():
        lat_min, lat_max = data["lat"]
        lng_min, lng_max = data["lng"]
        if lat_min <= latitude <= lat_max and lng_min <= longitude <= lng_max:
            return {
                "fine_zone_id": fine_zone_id,
                "parent_zone_id": str(data["parent_zone_id"]),
            }
    return None


def same_parent_zone(zone_a: str | None, zone_b: str | None) -> bool:
    if not zone_a or not zone_b:
        return False
    return parent_zone_for(zone_a) == parent_zone_for(zone_b)
