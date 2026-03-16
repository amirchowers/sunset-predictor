"""Daily sunset capture + prediction pipeline.

Captures frames from YouTube live webcams around sunset time.
Technique: YouTube live thumbnails (maxresdefault_live.jpg) update
every ~30-120s for active streams — no API key, no ffmpeg needed.

Usage:
    python3 capture_sunset.py              # capture one set now
    python3 capture_sunset.py --wait       # wait until sunset window, capture 3 sets
    python3 capture_sunset.py --rate       # capture + rate via vision AI
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from sunset_predictor.cameras import get_cameras
from sunset_predictor.config import DEFAULT_LOCATION
from sunset_predictor.fetcher import OpenMeteoFetcher
from sunset_predictor.scorer import calculate_sunset_score, get_verdict
from sunset_predictor.sun import get_sunset_info, get_western_sky_points

DATA_DIR = Path(__file__).parent / "calibration_data"


def capture_frame(camera, output_path: Path) -> bool:
    """Grab a single frame from a camera. Returns True if saved."""
    try:
        resp = requests.get(camera.image_url, timeout=15)
        resp.raise_for_status()
        if len(resp.content) < camera.min_size:
            print(f"  {camera.name}: too small ({len(resp.content)}b) — likely offline")
            return False
        output_path.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"  {camera.name}: error — {e}")
        return False


def check_camera_liveness(camera, prev_hash: str = None) -> tuple[bool, str]:
    """Quick check: is the camera serving a real, updated frame?
    Returns (is_live, content_hash).
    """
    try:
        resp = requests.get(camera.image_url, timeout=10)
        if resp.status_code != 200 or len(resp.content) < camera.min_size:
            return False, ""
        h = hashlib.md5(resp.content).hexdigest()
        if prev_hash and h == prev_hash:
            return False, h  # same frame = stale
        return True, h
    except Exception:
        return False, ""


def run_prediction(location):
    sun_info = get_sunset_info(
        location.lat, location.lon, location.timezone, location.name
    )
    western_points = get_western_sky_points(
        location.lat, location.lon, sun_info["azimuth"]
    )
    fetcher = OpenMeteoFetcher()
    weather = fetcher.get_weather_at_sunset(
        location.lat, location.lon, sun_info["sunset"]
    )
    air_quality = fetcher.get_air_quality(location.lat, location.lon)
    western_sky = fetcher.get_western_sky_weather(
        western_points, sun_info["sunset"]
    )
    result = calculate_sunset_score(weather, air_quality, western_sky)
    result["raw"]["comfort"] = weather.get("comfort")
    verdict = get_verdict(result["overall"])
    return sun_info, result, verdict


def capture_series(cameras, day_dir: Path, label: str) -> list[Path]:
    """Capture one frame from each camera with the given label."""
    paths = []
    for cam in cameras:
        filename = f"{cam.name}_{label}.jpg"
        path = day_dir / filename
        print(f"    {cam.name} [{label}]...", end=" ", flush=True)
        if capture_frame(cam, path):
            print(f"saved ({path.stat().st_size // 1024}KB)")
            paths.append(path)
        else:
            print("skipped")
    return paths


def to_manifest_path(image_path: Path) -> str:
    """Store image paths relative to calibration_data when possible."""
    try:
        return str(image_path.relative_to(DATA_DIR))
    except ValueError:
        return str(image_path)


def wait_until(target: datetime, tz_name: str):
    now = datetime.now(timezone.utc)
    wait_seconds = (target - now).total_seconds()
    if wait_seconds <= 0:
        return
    local = target.astimezone(ZoneInfo(tz_name))
    print(f"  Waiting until {local.strftime('%H:%M')} ({int(wait_seconds / 60)} min)...")
    while wait_seconds > 60:
        mins = int(wait_seconds / 60)
        print(f"    {mins} min remaining...", end="\r", flush=True)
        time.sleep(min(60, wait_seconds - 30))
        now = datetime.now(timezone.utc)
        wait_seconds = (target - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)


def main():
    parser = argparse.ArgumentParser(description="Capture sunset + prediction")
    parser.add_argument("--wait", action="store_true",
                        help="Wait until sunset window, then capture before/during/after")
    parser.add_argument("--rate", action="store_true",
                        help="Rate sunset via vision AI after capture")
    args = parser.parse_args()

    location = DEFAULT_LOCATION
    cameras = get_cameras()

    print(f"\n  Sunset Capture — {location.name}")
    print(f"  Cameras: {len(cameras)}")
    print()

    # --- Step 1: Prediction ---
    print("  [1/3] Prediction")
    sun_info, result, verdict = run_prediction(location)
    sunset_utc = sun_info["sunset"]
    sunset_local = sunset_utc.astimezone(ZoneInfo(location.timezone))
    print(f"    Score: {result['overall']}/10 — {verdict}")
    print(f"    Sunset: {sunset_local.strftime('%H:%M')} local")
    print()

    date_str = sunset_local.strftime("%Y-%m-%d")
    day_dir = DATA_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    prediction_data = {
        "date": date_str,
        "sunset_utc": sunset_utc.isoformat(),
        "sunset_local": sunset_local.strftime("%H:%M"),
        "azimuth": sun_info["azimuth"],
        "score": result["overall"],
        "verdict": verdict,
        "scores": result["scores"],
        "raw": {k: v for k, v in result["raw"].items() if k != "comfort"},
        "comfort": result["raw"].get("comfort"),
    }
    (day_dir / "prediction.json").write_text(
        json.dumps(prediction_data, indent=2, default=str)
    )

    # --- Step 2: Camera health check ---
    print("  [2/3] Camera check")
    live_cameras = []
    for cam in cameras:
        alive, _ = check_camera_liveness(cam)
        status = "live" if alive else "offline/stale"
        print(f"    {cam.name}: {status}")
        if alive:
            live_cameras.append(cam)
    print()

    if not live_cameras:
        print("  No live cameras available. Saving prediction only.")
        print()
    else:
        # --- Step 3: Capture ---
        print(f"  [3/3] Capturing from {len(live_cameras)} cameras")
        all_images = []

        if args.wait:
            # Full sunset window: -10min, sunset, +10min, +20min
            offsets = [
                (-10, "before"),
                (0, "sunset"),
                (10, "after_10"),
                (20, "after_20"),
            ]
            for offset_min, label in offsets:
                target = sunset_utc + timedelta(minutes=offset_min)
                wait_until(target, location.timezone)
                print(f"  --- {label} ---")
                all_images.extend(capture_series(live_cameras, day_dir, label))
                print()
        else:
            now_label = datetime.now(timezone.utc).strftime("%H%M")
            print(f"  --- Snapshot at {now_label} UTC ---")
            all_images.extend(capture_series(live_cameras, day_dir, f"t{now_label}"))
            print()

        manifest_images = [to_manifest_path(p) for p in all_images]
        missing_images = []
        for p in manifest_images:
            path_obj = Path(p)
            resolved = path_obj if path_obj.is_absolute() else (DATA_DIR / path_obj)
            if not resolved.exists():
                missing_images.append(str(path_obj))

        if missing_images:
            print("  Warning: some captured image files are missing on disk:")
            for p in missing_images:
                print(f"    - {p}")
            print()

        # Save manifest
        manifest = {
            "date": date_str,
            "images": manifest_images,
            "cameras": [c.name for c in live_cameras],
            "predicted_score": result["overall"],
            "human_score": None,
            "human_notes": "",
            "actual_score": None,
            "notes": "",
            "missing_images": missing_images,
        }
        (day_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # --- Summary ---
    img_count = len(list(day_dir.glob("*.jpg")))
    print(f"  === Done ===")
    print(f"  Date:       {date_str}")
    print(f"  Predicted:  {result['overall']}/10 — {verdict}")
    print(f"  Images:     {img_count} in {day_dir}/")
    print(f"  Rate it:    Set actual_score in {day_dir}/manifest.json")
    print()

    if args.rate:
        print("  Vision AI rating not yet configured.")
        print("  Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env to enable.")
        print()


if __name__ == "__main__":
    main()
