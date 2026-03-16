"""Sunset quality scoring engine.

Each factor is scored 1–10, then combined via weighted average.
Weights and thresholds are educated guesses for v1 — designed to be
recalibrated against real sunset quality data later.
"""

WEIGHTS = {
    "cloud_high": 0.15,
    "cloud_low_mid": 0.10,
    "western_near": 0.20,
    "western_far": 0.10,
    "humidity": 0.10,
    "visibility": 0.10,
    "air_quality": 0.10,
    "weather_condition": 0.15,
}

WEIGHTS_LEGACY = {
    "cloud_cover": 0.15,
    "western_near": 0.15,
    "western_far": 0.10,
    "humidity": 0.15,
    "visibility": 0.10,
    "air_quality": 0.15,
    "weather_condition": 0.20,
}


def _score_cloud_cover(pct: float) -> float:
    """Fallback when cloud layer data isn't available."""
    if pct <= 5:
        return 3.0
    if pct <= 20:
        return 5.5
    if pct <= 40:
        return 9.0
    if pct <= 60:
        return 10.0
    if pct <= 75:
        return 6.0
    if pct <= 90:
        return 3.0
    return 1.0


def _score_cloud_high(pct: float) -> float:
    """High clouds (6km+, cirrus/cirrostratus): the key sunset ingredient.

    Ice crystals refract and scatter light into vivid reds and oranges.
    Scattered high clouds are the single best predictor of a spectacular sunset.
    """
    if pct <= 5:
        return 4.0
    if pct <= 20:
        return 7.0
    if pct <= 50:
        return 10.0
    if pct <= 70:
        return 8.0
    if pct <= 85:
        return 5.0
    return 3.0


def _score_cloud_low_mid(low_pct: float, mid_pct: float) -> float:
    """Low (0-2km) and mid (2-6km) clouds block rather than beautify.

    Low clouds are worst — they sit right at the horizon and block the sun.
    Mid clouds in heavy amounts also dim the show.
    """
    if low_pct > 70:
        return 1.0
    if low_pct > 50:
        return 3.0
    impact = low_pct * 1.5 + mid_pct
    if impact > 120:
        return 1.0
    if impact > 80:
        return 3.0
    if impact > 50:
        return 5.0
    if impact > 20:
        return 8.0
    return 9.0


def _score_humidity(pct: float) -> float:
    if pct <= 30:
        return 10.0
    if pct <= 50:
        return 8.0
    if pct <= 65:
        return 6.0
    if pct <= 80:
        return 3.0
    return 1.0


def _score_visibility(meters: float) -> float:
    km = meters / 1000
    if km >= 10:
        return 10.0
    if km >= 7:
        return 8.0
    if km >= 4:
        return 5.0
    if km >= 2:
        return 3.0
    return 1.0


def _score_air_quality(pm25: float) -> float:
    """Moderate aerosols enhance color via scattering; too much = haze."""
    if pm25 <= 5:
        return 5.0
    if pm25 <= 15:
        return 7.0
    if pm25 <= 35:
        return 10.0
    if pm25 <= 55:
        return 6.0
    if pm25 <= 75:
        return 3.0
    return 1.0


def _score_western_near(cloud_pct: float, condition_id: int) -> float:
    """Near-west (~25km): is the sun blocked at the horizon?

    Overcast or precipitation in the sunset direction kills the show.
    Scattered clouds here are ideal — they catch light right at the horizon.
    """
    if 200 <= condition_id < 700:
        return 1.0
    if cloud_pct > 90:
        return 1.0
    if cloud_pct > 80:
        return 3.0
    if cloud_pct > 70:
        return 5.0
    if cloud_pct > 50:
        return 8.0
    if cloud_pct > 25:
        return 10.0
    if cloud_pct > 10:
        return 7.0
    return 5.0


def _score_western_far(cloud_pct: float) -> float:
    """Far-west (~80km): are there clouds to serve as a color canvas?

    Scattered-to-broken clouds at this distance catch reddened sunlight
    and produce the most dramatic color displays.
    """
    if cloud_pct <= 5:
        return 4.0
    if cloud_pct <= 20:
        return 6.0
    if cloud_pct <= 50:
        return 10.0
    if cloud_pct <= 70:
        return 8.0
    if cloud_pct <= 85:
        return 5.0
    return 2.0


def _score_weather_condition(condition_id: int, western_near_clouds: float = None) -> float:
    """Score weather conditions, cross-referencing western sky for overcast.

    Precipitation is always bad. For overcast skies, check whether the
    western horizon has gaps — if so, the sun can still break through
    at the waterline (the "gap sunset" effect).
    """
    if 200 <= condition_id < 300:
        return 1.0
    if 500 <= condition_id < 600:
        return 2.0
    if 600 <= condition_id < 700:
        return 1.0
    if 300 <= condition_id < 400:
        return 3.0
    if 700 <= condition_id < 800:
        return 3.0
    if condition_id == 800:
        return 6.0
    if condition_id == 801:
        return 8.0
    if condition_id == 802:
        return 10.0
    if condition_id == 803:
        return 8.0
    if condition_id == 804:
        if western_near_clouds is not None and western_near_clouds < 50:
            return 6.0
        if western_near_clouds is not None and western_near_clouds < 75:
            return 5.0
        return 2.0
    return 5.0


def calculate_sunset_score(
    weather: dict, air_quality: dict, western_sky: dict
) -> dict:
    cloud_pct = weather.get("clouds", {}).get("all", 0)
    humidity = weather.get("main", {}).get("humidity", 50)
    visibility = weather.get("visibility", 10000)

    conditions = weather.get("weather", [{"id": 800}])
    condition_id = conditions[0]["id"]

    components = air_quality.get("list", [{}])[0].get("components", {})
    pm25 = components.get("pm2_5", 10)

    near_weather = western_sky["near"]
    far_weather = western_sky["far"]
    near_clouds = near_weather.get("clouds", {}).get("all", 0)
    near_cond = near_weather.get("weather", [{"id": 800}])[0]["id"]
    far_clouds = far_weather.get("clouds", {}).get("all", 0)

    cloud_layers = weather.get("cloud_layers")
    has_layers = cloud_layers is not None

    if has_layers:
        scores = {
            "cloud_high": _score_cloud_high(cloud_layers["high"]),
            "cloud_low_mid": _score_cloud_low_mid(
                cloud_layers["low"], cloud_layers["mid"]
            ),
            "western_near": _score_western_near(near_clouds, near_cond),
            "western_far": _score_western_far(far_clouds),
            "humidity": _score_humidity(humidity),
            "visibility": _score_visibility(visibility),
            "air_quality": _score_air_quality(pm25),
            "weather_condition": _score_weather_condition(
                condition_id, near_clouds
            ),
        }
        weights = WEIGHTS
    else:
        scores = {
            "cloud_cover": _score_cloud_cover(cloud_pct),
            "western_near": _score_western_near(near_clouds, near_cond),
            "western_far": _score_western_far(far_clouds),
            "humidity": _score_humidity(humidity),
            "visibility": _score_visibility(visibility),
            "air_quality": _score_air_quality(pm25),
            "weather_condition": _score_weather_condition(
                condition_id, near_clouds
            ),
        }
        weights = WEIGHTS_LEGACY

    overall = sum(scores[k] * weights[k] for k in weights)

    raw = {
        "cloud_cover_pct": cloud_pct,
        "humidity_pct": humidity,
        "visibility_km": round(visibility / 1000, 1),
        "pm2_5": round(pm25, 1),
        "condition": conditions[0].get("description", "unknown"),
        "condition_id": condition_id,
        "western_near_clouds_pct": near_clouds,
        "western_far_clouds_pct": far_clouds,
    }
    if has_layers:
        raw["cloud_high_pct"] = cloud_layers["high"]
        raw["cloud_mid_pct"] = cloud_layers["mid"]
        raw["cloud_low_pct"] = cloud_layers["low"]

    return {
        "overall": round(overall, 1),
        "scores": scores,
        "raw": raw,
        "has_cloud_layers": has_layers,
    }


def get_verdict(score: float) -> str:
    if score >= 8.0:
        return "Tell your friends — rare show"
    if score >= 6.5:
        return "Worth making plans for"
    if score >= 5.0:
        return "Watchable — sun meets the sea"
    if score >= 3.5:
        return "Probably blocked or dull"
    return "Skip it"
