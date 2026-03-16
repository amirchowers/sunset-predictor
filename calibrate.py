"""Batch Vision AI rating for calibration images.

Loads captured webcam images for a given date, runs the Gemini/HuggingFace
rater, and writes the AI score back into that day's manifest.json.

Usage:
    python3 calibrate.py --date 2026-02-25
    python3 calibrate.py                     # defaults to today
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "calibration_data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("calibrate")


def parse_date(date_str: str) -> str:
    """Validate and return a YYYY-MM-DD date string."""
    datetime.strptime(date_str, "%Y-%m-%d")
    return date_str


def find_images(day_dir: Path) -> list:
    """Return sorted list of .jpg Paths in a day directory."""
    if not day_dir.is_dir():
        return []
    return sorted(day_dir.glob("*.jpg"))


def load_manifest(day_dir: Path) -> dict:
    """Load manifest.json from a day directory, or return empty dict."""
    manifest_path = day_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, Exception):
        return {}


def save_ai_rating(day_dir: Path, ai_result: dict):
    """Merge AI rating into existing manifest.json."""
    manifest = load_manifest(day_dir)
    manifest["ai_score"] = ai_result.get("ai_score")
    manifest["ai_ratings"] = ai_result.get("ratings", [])
    (day_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Batch Vision AI rating for calibration images")
    parser.add_argument(
        "--date", type=str, default=None,
        help="Date to rate (YYYY-MM-DD). Defaults to today.",
    )
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    try:
        date_str = parse_date(date_str)
    except ValueError:
        log.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
        sys.exit(1)

    day_dir = DATA_DIR / date_str
    if not day_dir.is_dir():
        log.error(f"No calibration data for {date_str}: {day_dir} does not exist")
        sys.exit(1)

    images = find_images(day_dir)
    if not images:
        log.error(f"No .jpg images found in {day_dir}")
        sys.exit(1)

    log.info(f"Rating {len(images)} images for {date_str}...")

    from sunset_predictor.rater import rate_sunset_images

    ai_result = rate_sunset_images(images)

    log.info(f"AI score: {ai_result['ai_score']}/10 ({ai_result['ratings_count']} images rated)")

    save_ai_rating(day_dir, ai_result)
    log.info(f"Saved to {day_dir / 'manifest.json'}")

    manifest = load_manifest(day_dir)
    predicted = manifest.get("predicted_score")
    human = manifest.get("human_score")
    ai = manifest.get("ai_score")
    log.info(f"Scores — predicted: {predicted}, AI: {ai}, human: {human}")


if __name__ == "__main__":
    main()
