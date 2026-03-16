import math
from datetime import datetime, timedelta, timezone

from astral import LocationInfo
from astral.sun import sun, azimuth


def get_sunset_info(lat: float, lon: float, tz_name: str, location_name: str = "") -> dict:
    """Calculate sunset time and azimuth. If today's sunset has passed, returns tomorrow's."""
    loc = LocationInfo(location_name, "", tz_name, lat, lon)
    now = datetime.now(timezone.utc)
    s = sun(loc.observer, date=now.date(), tzinfo=timezone.utc)

    if now > s["sunset"]:
        tomorrow = now.date() + timedelta(days=1)
        s = sun(loc.observer, date=tomorrow, tzinfo=timezone.utc)

    sunset_azimuth = azimuth(loc.observer, s["sunset"])

    return {
        "sunset": s["sunset"],
        "sunrise": s["sunrise"],
        "date": s["sunset"].date(),
        "azimuth": sunset_azimuth,
    }


def point_along_bearing(lat: float, lon: float, bearing_deg: float, distance_km: float):
    """Return (lat, lon) of a point at given distance along a compass bearing.

    Uses flat-earth approximation — accurate enough for distances under 200km.
    """
    bearing_rad = math.radians(bearing_deg)
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(lat))

    delta_lat = distance_km * math.cos(bearing_rad) / km_per_deg_lat
    delta_lon = distance_km * math.sin(bearing_rad) / km_per_deg_lon

    return (lat + delta_lat, lon + delta_lon)


def get_western_sky_points(lat: float, lon: float, azimuth_deg: float):
    """Return two (lat, lon) points along the sunset azimuth.

    Near point (~25km): detects horizon blocking.
    Far point (~80km): detects color-catching cloud canvas.
    """
    near = point_along_bearing(lat, lon, azimuth_deg, 25)
    far = point_along_bearing(lat, lon, azimuth_deg, 80)
    return {"near": near, "far": far}
