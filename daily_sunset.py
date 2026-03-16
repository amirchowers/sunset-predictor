"""Automated daily sunset pipeline with multi-timepoint predictions.

Designed to be triggered by launchd/cron multiple times per day:
  1. Morning   (~08:00) — early prediction snapshot
  2. Noon      (~12:00) — mid-day prediction snapshot
  3. Pre-sunset (~30min before) — final prediction + webcam capture at sunset window

Each invocation appends a timestamped prediction to predictions.json.
The pre-sunset run also captures webcam frames at -10, 0, +10, +20 min.

Usage:
    python3 daily_sunset.py                # log prediction now
    python3 daily_sunset.py --capture      # log prediction + capture at sunset window
    python3 daily_sunset.py --capture --now  # log prediction + capture immediately (no wait)
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sunset_predictor.cameras import get_cameras
from sunset_predictor.config import DEFAULT_LOCATION
from sunset_predictor.fetcher import OpenMeteoFetcher
from sunset_predictor.notifier import send_prediction
from sunset_predictor.scorer import calculate_sunset_score, get_verdict
from sunset_predictor.sun import get_sunset_info, get_western_sky_points

DATA_DIR = Path(__file__).parent / "calibration_data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("daily_sunset")


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

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


def build_prediction_entry(sun_info, result, verdict, location):
    now_utc = datetime.now(timezone.utc)
    sunset_utc = sun_info["sunset"]
    sunset_local = sunset_utc.astimezone(ZoneInfo(location.timezone))
    hours_before = (sunset_utc - now_utc).total_seconds() / 3600

    return {
        "predicted_at_utc": now_utc.isoformat(),
        "predicted_at_local": now_utc.astimezone(ZoneInfo(location.timezone)).strftime("%H:%M"),
        "hours_before_sunset": round(hours_before, 1),
        "score": result["overall"],
        "verdict": verdict,
        "scores": result["scores"],
        "raw": {k: v for k, v in result["raw"].items() if k != "comfort"},
        "comfort": result["raw"].get("comfort"),
        "sunset_utc": sunset_utc.isoformat(),
        "sunset_local": sunset_local.strftime("%H:%M"),
        "azimuth": sun_info["azimuth"],
    }


def append_prediction(day_dir: Path, entry: dict):
    """Append a prediction entry to the day's predictions.json list."""
    predictions_file = day_dir / "predictions.json"
    predictions = []
    if predictions_file.exists():
        try:
            predictions = json.loads(predictions_file.read_text())
        except (json.JSONDecodeError, Exception):
            predictions = []

    predictions.append(entry)
    predictions_file.write_text(json.dumps(predictions, indent=2, default=str))
    return predictions


# ---------------------------------------------------------------------------
# Webcam capture (reuses capture_sunset.py logic)
# ---------------------------------------------------------------------------

def capture_frame(camera, output_path: Path) -> bool:
    import requests
    try:
        resp = requests.get(camera.image_url, timeout=15)
        resp.raise_for_status()
        if len(resp.content) < camera.min_size:
            log.warning(f"{camera.name}: too small ({len(resp.content)}b) — offline/placeholder")
            return False
        output_path.write_bytes(resp.content)
        return True
    except Exception as e:
        log.warning(f"{camera.name}: capture error — {e}")
        return False


def capture_series(cameras, day_dir: Path, label: str) -> list[str]:
    """Capture one frame per camera, return relative paths."""
    paths = []
    for cam in cameras:
        filename = f"{cam.name}_{label}.jpg"
        path = day_dir / filename
        if capture_frame(cam, path):
            log.info(f"  {cam.name} [{label}]: saved ({path.stat().st_size // 1024}KB)")
            try:
                paths.append(str(path.relative_to(DATA_DIR)))
            except ValueError:
                paths.append(str(path))
        else:
            log.info(f"  {cam.name} [{label}]: skipped")
    return paths


def check_camera_liveness(camera) -> bool:
    import requests
    try:
        resp = requests.get(camera.image_url, timeout=10)
        return resp.status_code == 200 and len(resp.content) >= camera.min_size
    except Exception:
        return False


def wait_until(target: datetime):
    now = datetime.now(timezone.utc)
    wait_seconds = (target - now).total_seconds()
    if wait_seconds <= 0:
        return
    log.info(f"Waiting {int(wait_seconds / 60)} min until {target.isoformat()}...")
    while wait_seconds > 60:
        time.sleep(min(60, wait_seconds - 30))
        now = datetime.now(timezone.utc)
        wait_seconds = (target - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)


def run_capture(sunset_utc: datetime, day_dir: Path, immediate: bool = False):
    """Capture webcam frames around sunset. If immediate, capture once now."""
    cameras = get_cameras()
    live_cameras = [c for c in cameras if check_camera_liveness(c)]

    log.info(f"Cameras: {len(live_cameras)}/{len(cameras)} live")

    if not live_cameras:
        log.warning("No live cameras — skipping capture")
        return []

    all_images = []

    if immediate:
        label = datetime.now(timezone.utc).strftime("t%H%M")
        log.info(f"Immediate capture: {label}")
        all_images.extend(capture_series(live_cameras, day_dir, label))
    else:
        offsets = [
            (-5, "pre_sunset"),
            (0, "sunset"),
            (5, "peak"),
            (15, "afterglow"),
        ]
        for offset_min, label in offsets:
            target = sunset_utc + timedelta(minutes=offset_min)
            wait_until(target)
            log.info(f"--- Capturing: {label} ---")
            all_images.extend(capture_series(live_cameras, day_dir, label))

    return all_images


def rate_images_if_possible(day_dir: Path, image_paths: list) -> dict:
    """Run Vision AI rating on captured images if any API key is available."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_hf = bool(os.getenv("HUGGINGFACE_API_KEY"))
    if not has_gemini and not has_hf:
        log.info("No GEMINI_API_KEY or HUGGINGFACE_API_KEY — skipping Vision AI rating")
        return {}

    try:
        from sunset_predictor.rater import rate_sunset_images
    except ImportError as e:
        log.warning(f"Cannot import rater: {e}")
        return {}

    resolved = []
    for p in image_paths:
        path = Path(p)
        if not path.is_absolute():
            path = DATA_DIR / path
        if path.exists():
            resolved.append(path)

    if not resolved:
        log.info("No images to rate")
        return {}

    log.info(f"Rating {len(resolved)} images via Vision AI...")
    try:
        result = rate_sunset_images(resolved)
        log.info(f"AI sunset score: {result.get('ai_score')}/10 ({result.get('ratings_count')} images rated)")
        return result
    except Exception as e:
        log.error(f"Vision AI rating failed: {e}")
        return {}


def save_manifest(day_dir: Path, predictions: list, images: list, cameras_used: list, ai_rating: dict = None):
    """Write/update manifest with latest prediction + images + AI rating."""
    manifest_path = day_dir / "manifest.json"

    existing = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
        except Exception:
            existing = {}

    latest_pred = predictions[-1] if predictions else {}
    all_images = list(set(existing.get("images", []) + images))

    manifest = {
        "date": day_dir.name,
        "images": sorted(all_images),
        "cameras": cameras_used,
        "predicted_score": latest_pred.get("score"),
        "prediction_count": len(predictions),
        "prediction_spread": {
            "earliest": predictions[0].get("score") if predictions else None,
            "latest": latest_pred.get("score"),
            "hours_range": f"{predictions[0].get('hours_before_sunset', '?')}h to {latest_pred.get('hours_before_sunset', '?')}h"
            if len(predictions) > 1 else None,
        },
        "ai_score": ai_rating.get("ai_score") if ai_rating else existing.get("ai_score"),
        "ai_ratings": ai_rating.get("ratings") if ai_rating else existing.get("ai_ratings"),
        "human_score": existing.get("human_score"),
        "human_notes": existing.get("human_notes", ""),
        "actual_score": existing.get("actual_score"),
        "notes": existing.get("notes", ""),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Daily sunset prediction + capture")
    parser.add_argument("--capture", action="store_true",
                        help="Also capture webcam frames around sunset")
    parser.add_argument("--now", action="store_true",
                        help="With --capture: capture immediately instead of waiting for sunset window")
    parser.add_argument("--notify", action="store_true",
                        help="Send prediction to Telegram")
    args = parser.parse_args()

    location = DEFAULT_LOCATION

    # --- Predict ---
    log.info(f"Running prediction for {location.name}")
    try:
        sun_info, result, verdict = run_prediction(location)
    except Exception as e:
        log.error(f"Prediction failed: {e}")
        sys.exit(1)

    sunset_utc = sun_info["sunset"]
    sunset_local = sunset_utc.astimezone(ZoneInfo(location.timezone))
    date_str = sunset_local.strftime("%Y-%m-%d")
    day_dir = DATA_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    entry = build_prediction_entry(sun_info, result, verdict, location)
    predictions = append_prediction(day_dir, entry)

    log.info(
        f"Score: {result['overall']}/10 — {verdict} "
        f"(predicted {entry['hours_before_sunset']}h before sunset)"
    )
    log.info(f"Sunset: {sunset_local.strftime('%H:%M')} local | Predictions today: {len(predictions)}")

    # --- Capture ---
    images = []
    cameras_used = []
    if args.capture:
        log.info("Starting webcam capture...")
        cameras = get_cameras()
        cameras_used = [c.name for c in cameras]
        images = run_capture(sunset_utc, day_dir, immediate=args.now)
        log.info(f"Captured {len(images)} images")

    # --- Vision AI Rating ---
    ai_rating = {}
    if args.capture and images:
        ai_rating = rate_images_if_possible(day_dir, images)

    # --- Manifest ---
    save_manifest(day_dir, predictions, images, cameras_used, ai_rating)

    # --- Log file ---
    log_path = day_dir / "daily.log"
    with open(log_path, "a") as f:
        f.write(
            f"{entry['predicted_at_utc']} | "
            f"score={result['overall']} | "
            f"hours_before={entry['hours_before_sunset']} | "
            f"images={len(images)}\n"
        )

    log.info(f"Data saved to {day_dir}/")

    # --- Notify ---
    if args.notify:
        send_prediction(result, verdict, sun_info, location)


if __name__ == "__main__":
    main()
