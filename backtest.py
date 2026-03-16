"""Backtest sunset predictor against 12 months of historical weather data.

Uses Open-Meteo free archive API (no key needed) for historical weather
and air quality. Scores each day's sunset and outputs results to CSV +
console summary of all 8+ days for manual cross-referencing with media.

Known simplification: uses average azimuth (270°) for western sky check
points instead of the exact daily azimuth. Error is small (~10km lateral
at 25km distance) compared to weather data granularity.
"""

import csv
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from sunset_predictor.scorer import calculate_sunset_score, get_verdict
from sunset_predictor.sun import get_sunset_info, point_along_bearing

# --- Config ---

LAT, LON = 32.0853, 34.7818
TZ_NAME = "Asia/Jerusalem"
LOCATION_NAME = "Tel Aviv"
AVG_AZIMUTH = 270.0

START_DATE = date(2025, 2, 1)
END_DATE = date(2026, 2, 1)

NEAR_KM = 25
FAR_KM = 80

OUTPUT_CSV = Path(__file__).parent / "backtest_results.csv"
RESULT_FIELDS = [
    "date",
    "sunset_utc",
    "score",
    "verdict",
    "clouds",
    "cloud_high",
    "cloud_mid",
    "cloud_low",
    "west_near_clouds",
    "west_far_clouds",
    "humidity",
    "visibility_km",
    "pm2_5",
    "condition",
]

# --- WMO weather code → OWM condition code mapping ---

_WMO_TO_OWM = {
    0: 800, 1: 801, 2: 802, 3: 804,
    45: 741, 48: 741,
    51: 300, 53: 300, 55: 300, 56: 300, 57: 300,
    61: 500, 63: 500, 65: 500, 66: 500, 67: 500,
    71: 600, 73: 600, 75: 600, 77: 600,
    80: 500, 81: 500, 82: 500,
    85: 600, 86: 600,
    95: 200, 96: 200, 99: 200,
}

WMO_DESCRIPTIONS = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm w/ hail", 99: "thunderstorm w/ hail",
}


def wmo_to_owm(code):
    if code is None:
        return 800
    return _WMO_TO_OWM.get(int(code), 800)


def wmo_description(code):
    if code is None:
        return "unknown"
    return WMO_DESCRIPTIONS.get(int(code), f"wmo_{code}")


# --- Open-Meteo data fetching ---

def fetch_weather_archive(lat, lon, start, end):
    resp = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": "cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,relative_humidity_2m,visibility,weather_code",
            "timezone": "UTC",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["hourly"]


def fetch_air_quality_archive(lat, lon, start, end):
    resp = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": "pm2_5",
            "timezone": "UTC",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["hourly"]


# --- Helpers ---

def build_time_index(hourly_times):
    """Map 'YYYY-MM-DDTHH:00' strings to array indices for fast lookup."""
    return {t: i for i, t in enumerate(hourly_times)}


def get_value_at_hour(hourly_data, field, time_index, hour_key, default):
    idx = time_index.get(hour_key)
    if idx is None:
        return default
    val = hourly_data[field][idx]
    return default if val is None else val


def to_owm_weather_dict(cloud_cover, humidity, visibility_m, weather_code):
    """Build an OWM-compatible dict from raw values so the scorer works as-is."""
    owm_id = wmo_to_owm(weather_code)
    return {
        "clouds": {"all": cloud_cover},
        "main": {"humidity": humidity},
        "visibility": visibility_m,
        "weather": [{"id": owm_id, "description": wmo_description(weather_code)}],
    }


def to_owm_air_dict(pm25):
    return {"list": [{"components": {"pm2_5": pm25}}]}


# --- Main ---

def main():
    near_lat, near_lon = point_along_bearing(LAT, LON, AVG_AZIMUTH, NEAR_KM)
    far_lat, far_lon = point_along_bearing(LAT, LON, AVG_AZIMUTH, FAR_KM)

    print(f"Fetching 12 months of historical data ({START_DATE} to {END_DATE})...")
    print(f"  Local:     {LAT:.2f}, {LON:.2f}")
    print(f"  Near-west: {near_lat:.2f}, {near_lon:.2f}  ({NEAR_KM}km @ {AVG_AZIMUTH}°)")
    print(f"  Far-west:  {far_lat:.2f}, {far_lon:.2f}  ({FAR_KM}km @ {AVG_AZIMUTH}°)")
    print()

    print("  [1/4] Weather — local...", end="", flush=True)
    local_weather = fetch_weather_archive(LAT, LON, START_DATE, END_DATE)
    print(" done")

    print("  [2/4] Weather — near-west...", end="", flush=True)
    near_weather = fetch_weather_archive(near_lat, near_lon, START_DATE, END_DATE)
    print(" done")

    print("  [3/4] Weather — far-west...", end="", flush=True)
    far_weather = fetch_weather_archive(far_lat, far_lon, START_DATE, END_DATE)
    print(" done")

    print("  [4/4] Air quality — local...", end="", flush=True)
    try:
        air_data = fetch_air_quality_archive(LAT, LON, START_DATE, END_DATE)
        has_air = True
    except Exception:
        air_data = {"time": [], "pm2_5": []}
        has_air = False
        print(" unavailable (using default PM2.5=15)", end="")
    print(" done")
    print()

    local_idx = build_time_index(local_weather["time"])
    near_idx = build_time_index(near_weather["time"])
    far_idx = build_time_index(far_weather["time"])
    air_idx = build_time_index(air_data["time"]) if has_air else {}

    results = []
    skipped_days = 0
    error_counts = {}
    error_samples = []
    current = START_DATE
    while current <= END_DATE:
        try:
            # Compute sunset for the specific historical date (UTC).
            from astral import LocationInfo
            from astral.sun import sun as compute_sun
            loc = LocationInfo(LOCATION_NAME, "", TZ_NAME, LAT, LON)
            s = compute_sun(loc.observer, date=current, tzinfo=timezone.utc)
            sunset_utc = s["sunset"]
        except Exception as exc:
            skipped_days += 1
            error_name = type(exc).__name__
            error_counts[error_name] = error_counts.get(error_name, 0) + 1
            if len(error_samples) < 8:
                error_samples.append(
                    f"{current.isoformat()} | {error_name}: {exc}"
                )
            current += timedelta(days=1)
            continue

        hour_key = sunset_utc.strftime("%Y-%m-%dT%H:00")

        cloud = get_value_at_hour(local_weather, "cloud_cover", local_idx, hour_key, 0)
        cloud_low = get_value_at_hour(local_weather, "cloud_cover_low", local_idx, hour_key, 0)
        cloud_mid = get_value_at_hour(local_weather, "cloud_cover_mid", local_idx, hour_key, 0)
        cloud_high = get_value_at_hour(local_weather, "cloud_cover_high", local_idx, hour_key, 0)
        humidity = get_value_at_hour(local_weather, "relative_humidity_2m", local_idx, hour_key, 50)
        vis = get_value_at_hour(local_weather, "visibility", local_idx, hour_key, 10000)
        wcode = get_value_at_hour(local_weather, "weather_code", local_idx, hour_key, 0)

        near_cloud = get_value_at_hour(near_weather, "cloud_cover", near_idx, hour_key, 0)
        near_wcode = get_value_at_hour(near_weather, "weather_code", near_idx, hour_key, 0)

        far_cloud = get_value_at_hour(far_weather, "cloud_cover", far_idx, hour_key, 0)

        pm25 = get_value_at_hour(air_data, "pm2_5", air_idx, hour_key, 15) if has_air else 15.0

        weather_dict = to_owm_weather_dict(cloud, humidity, vis, wcode)
        weather_dict["cloud_layers"] = {
            "low": cloud_low,
            "mid": cloud_mid,
            "high": cloud_high,
        }
        air_dict = to_owm_air_dict(pm25)
        western_dict = {
            "near": to_owm_weather_dict(near_cloud, 50, 10000, near_wcode),
            "far": to_owm_weather_dict(far_cloud, 50, 10000, 0),
        }

        result = calculate_sunset_score(weather_dict, air_dict, western_dict)
        verdict = get_verdict(result["overall"])

        results.append({
            "date": current.isoformat(),
            "sunset_utc": sunset_utc.strftime("%H:%M"),
            "score": result["overall"],
            "verdict": verdict,
            "clouds": cloud,
            "cloud_high": cloud_high,
            "cloud_mid": cloud_mid,
            "cloud_low": cloud_low,
            "west_near_clouds": near_cloud,
            "west_far_clouds": far_cloud,
            "humidity": humidity,
            "visibility_km": round(vis / 1000, 1) if vis else 10.0,
            "pm2_5": round(pm25, 1),
            "condition": wmo_description(wcode),
        })

        current += timedelta(days=1)

    # Save CSV (always write headers, even if no rows).
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    if not results:
        print("  No valid backtest rows generated.")
        print(f"  Skipped days: {skipped_days}")
        if error_counts:
            print("  Error summary:")
            for name, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"    {name}: {count}")
        if error_samples:
            print("  Example failures:")
            for sample in error_samples:
                print(f"    {sample}")
        print()
        print(f"  Empty results CSV saved to: {OUTPUT_CSV}")
        sys.exit(1)

    # Console summary
    scores = [r["score"] for r in results]
    top_days = [r for r in results if r["score"] >= 8.0]
    top_days.sort(key=lambda r: r["score"], reverse=True)

    print(f"  Scored {len(results)} days ({START_DATE} to {END_DATE})")
    if skipped_days:
        print(f"  Skipped days due to errors: {skipped_days}")
    if error_counts:
        print("  Error summary:")
        for name, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {name}: {count}")
    if error_samples:
        print("  Example failures:")
        for sample in error_samples:
            print(f"    {sample}")
    print(f"  Average score: {sum(scores) / len(scores):.1f}")
    print(f"  Days scoring 8+: {len(top_days)}")
    print()

    # Score distribution
    buckets = {"9-10": 0, "8-9": 0, "7-8": 0, "6-7": 0, "5-6": 0, "4-5": 0, "3-4": 0, "1-3": 0}
    for s in scores:
        if s >= 9: buckets["9-10"] += 1
        elif s >= 8: buckets["8-9"] += 1
        elif s >= 7: buckets["7-8"] += 1
        elif s >= 6: buckets["6-7"] += 1
        elif s >= 5: buckets["5-6"] += 1
        elif s >= 4: buckets["4-5"] += 1
        elif s >= 3: buckets["3-4"] += 1
        else: buckets["1-3"] += 1

    print("  Score distribution:")
    for bucket, count in buckets.items():
        bar = "#" * count
        print(f"    {bucket:>5}: {count:>3}  {bar}")
    print()

    if top_days:
        print("  === Days scoring 8+ (cross-reference with media) ===")
        print(f"  {'Date':<12} {'Score':>5}  {'Hi':>3} {'Mid':>3} {'Low':>3}  {'W-nr':>4} {'W-fr':>4} {'Hum':>4} {'PM25':>4}  Condition")
        print(f"  {'-'*80}")
        for r in top_days:
            print(
                f"  {r['date']:<12} {r['score']:>5.1f}  "
                f"{r['cloud_high']:>3} {r['cloud_mid']:>3} {r['cloud_low']:>3}  "
                f"{r['west_near_clouds']:>3}% {r['west_far_clouds']:>3}% "
                f"{r['humidity']:>3}% {r['pm2_5']:>4}  {r['condition']}"
            )
    else:
        print("  No days scored 8+. Model weights may need tuning.")

    print()
    print(f"  Full results saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
