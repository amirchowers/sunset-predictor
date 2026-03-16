"""Weather data fetcher using Open-Meteo (free, no API key needed).

Provides cloud layers (low/mid/high), wind, temperature, and air quality
data — all the signals needed for sunset scoring and comfort warnings.
"""

from datetime import datetime, timezone

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

HOURLY_VARS = (
    "cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,"
    "relative_humidity_2m,visibility,weather_code,"
    "wind_speed_10m,wind_gusts_10m,temperature_2m,apparent_temperature"
)

WMO_TO_OWM = {
    0: 800, 1: 801, 2: 802, 3: 804,
    45: 741, 48: 741,
    51: 300, 53: 300, 55: 300, 56: 300, 57: 300,
    61: 500, 63: 500, 65: 500, 66: 500, 67: 500,
    71: 600, 73: 600, 75: 600, 77: 600,
    80: 500, 81: 500, 82: 500,
    85: 600, 86: 600,
    95: 200, 96: 200, 99: 200,
}

WMO_DESC = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    56: "freezing drizzle", 57: "freezing drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    66: "freezing rain", 67: "freezing rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm w/ hail", 99: "thunderstorm w/ hail",
}


class OpenMeteoFetcher:
    def _fetch_hourly(self, url: str, lat: float, lon: float, hourly: str) -> dict:
        resp = requests.get(
            url,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": hourly,
                "forecast_days": 2,
                "timezone": "UTC",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["hourly"]

    def _find_closest_index(self, times: list, target: datetime) -> int:
        target_key = target.strftime("%Y-%m-%dT%H:00")
        for i, t in enumerate(times):
            if t == target_key:
                return i
        return min(
            range(len(times)),
            key=lambda i: abs(
                datetime.fromisoformat(times[i]).replace(tzinfo=timezone.utc) - target
            ),
        )

    def _val(self, data, field, idx, default=0):
        v = data[field][idx]
        return default if v is None else v

    def get_weather_at_sunset(self, lat: float, lon: float, sunset_time: datetime) -> dict:
        data = self._fetch_hourly(FORECAST_URL, lat, lon, HOURLY_VARS)
        idx = self._find_closest_index(data["time"], sunset_time)

        wmo = self._val(data, "weather_code", idx, 0)
        wmo = int(wmo)
        owm_id = WMO_TO_OWM.get(wmo, 800)

        return {
            "clouds": {"all": self._val(data, "cloud_cover", idx)},
            "cloud_layers": {
                "low": self._val(data, "cloud_cover_low", idx),
                "mid": self._val(data, "cloud_cover_mid", idx),
                "high": self._val(data, "cloud_cover_high", idx),
            },
            "main": {"humidity": self._val(data, "relative_humidity_2m", idx, 50)},
            "visibility": self._val(data, "visibility", idx, 10000),
            "weather": [{"id": owm_id, "description": WMO_DESC.get(wmo, f"wmo_{wmo}")}],
            "comfort": {
                "temp_c": self._val(data, "temperature_2m", idx),
                "feels_like_c": self._val(data, "apparent_temperature", idx),
                "wind_kmh": self._val(data, "wind_speed_10m", idx),
                "wind_gusts_kmh": self._val(data, "wind_gusts_10m", idx),
            },
        }

    def get_air_quality(self, lat: float, lon: float) -> dict:
        data = self._fetch_hourly(AIR_QUALITY_URL, lat, lon, "pm2_5")
        latest_pm25 = next(
            (v for v in reversed(data["pm2_5"]) if v is not None), 10
        )
        return {"list": [{"components": {"pm2_5": latest_pm25}}]}

    def get_western_sky_weather(
        self, western_points: dict, sunset_time: datetime
    ) -> dict:
        result = {}
        for key in ("near", "far"):
            lat, lon = western_points[key]
            result[key] = self.get_weather_at_sunset(lat, lon, sunset_time)
        return result
