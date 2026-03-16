from zoneinfo import ZoneInfo


def print_prediction(location, sun_info: dict, result: dict, verdict: str) -> None:
    sunset_local = sun_info["sunset"].astimezone(ZoneInfo(location.timezone))
    date_str = sunset_local.strftime("%A, %b %d, %Y")
    time_str = sunset_local.strftime("%H:%M")
    azimuth = sun_info["azimuth"]

    raw = result["raw"]
    scores = result["scores"]
    overall = result["overall"]
    has_layers = result.get("has_cloud_layers", False)

    bar = _score_bar(overall)

    print()
    print(f"  Sunset Prediction — {location.name}")
    print(f"  {date_str}")
    print(f"  Sunset at {time_str} local time  (azimuth {azimuth:.0f}°)")
    print()
    print(f"  Score: {overall}/10  {bar}")
    print(f"  Verdict: {verdict}")
    print()
    print("  Breakdown:")
    if has_layers:
        _print_factor("High clouds", f"{raw['cloud_high_pct']}%", scores["cloud_high"])
        _print_factor("Low/mid clouds", f"{raw['cloud_low_pct']}% / {raw['cloud_mid_pct']}%", scores["cloud_low_mid"])
    else:
        _print_factor("Cloud cover", f"{raw['cloud_cover_pct']}%", scores["cloud_cover"])
    _print_factor("West (near)", f"{raw['western_near_clouds_pct']}% clouds", scores["western_near"])
    _print_factor("West (far)", f"{raw['western_far_clouds_pct']}% clouds", scores["western_far"])
    _print_factor("Humidity", f"{raw['humidity_pct']}%", scores["humidity"])
    _print_factor("Visibility", f"{raw['visibility_km']} km", scores["visibility"])
    _print_factor("Air quality", f"PM2.5 {raw['pm2_5']}", scores["air_quality"])
    _print_factor("Conditions", raw["condition"], scores["weather_condition"])

    comfort = raw.get("comfort")
    if comfort:
        _print_comfort(comfort)

    print()


def _print_factor(name: str, value: str, score: float) -> None:
    print(f"    {name:<14} {value:<18} {score:.0f}/10")


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(round(score / 10 * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def _print_comfort(comfort: dict) -> None:
    warnings = []
    wind = comfort.get("wind_kmh", 0)
    gusts = comfort.get("wind_gusts_kmh", 0)
    temp = comfort.get("temp_c", 20)
    feels = comfort.get("feels_like_c", temp)

    if wind >= 40:
        warnings.append(f"Very windy: {wind:.0f} km/h (gusts {gusts:.0f})")
    elif wind >= 25:
        warnings.append(f"Windy: {wind:.0f} km/h (gusts {gusts:.0f})")

    if feels < 8:
        warnings.append(f"Cold: {temp:.0f}°C (feels like {feels:.0f}°C) — dress warm")
    elif feels < 15:
        warnings.append(f"Cool: {temp:.0f}°C (feels like {feels:.0f}°C) — bring a layer")

    if not warnings:
        return

    print()
    print("  Heads up:")
    for w in warnings:
        print(f"    {w}")
