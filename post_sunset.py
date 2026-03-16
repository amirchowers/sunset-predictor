"""Post sunset content to Instagram.

Two modes:
  --prediction  Generate and post the noon prediction card (score + tip)
  --photo       Post the evening sunset photo (best frame + score overlay)

Usage:
    python3 post_sunset.py --prediction     # noon: prediction card with AI tip
    python3 post_sunset.py --photo          # evening: best sunset frame
    python3 post_sunset.py --prediction --dry-run  # generate card without posting
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sunset_predictor.config import DEFAULT_LOCATION
from sunset_predictor.poster import (
    build_evening_caption,
    build_noon_caption,
    generate_prediction_card,
    generate_tip,
    overlay_score,
    post_to_instagram,
    select_best_frame,
    should_post_evening,
)
from sunset_predictor.scorer import get_verdict

DATA_DIR = Path(__file__).parent / "calibration_data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("post_sunset")


def _get_today_dir() -> Path:
    tz = ZoneInfo(DEFAULT_LOCATION.timezone)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    return DATA_DIR / today


def _load_latest_prediction(day_dir: Path) -> dict:
    pred_file = day_dir / "predictions.json"
    if not pred_file.exists():
        log.error(f"No predictions.json in {day_dir}")
        sys.exit(1)
    predictions = json.loads(pred_file.read_text())
    if not predictions:
        log.error("predictions.json is empty")
        sys.exit(1)
    return predictions[-1]


def _load_manifest(day_dir: Path) -> dict:
    manifest_file = day_dir / "manifest.json"
    if not manifest_file.exists():
        return {}
    return json.loads(manifest_file.read_text())


def run_prediction_post(dry_run: bool = False):
    """Generate and post the noon prediction card."""
    day_dir = _get_today_dir()
    if not day_dir.exists():
        log.error(f"No data directory for today: {day_dir}")
        sys.exit(1)

    pred = _load_latest_prediction(day_dir)

    log.info(f"Score: {pred['score']}/10 — {pred['verdict']}")
    log.info("Generating lifestyle tip via Gemini...")
    tip = generate_tip(pred)
    if tip:
        log.info(f"Tip: {tip}")
    else:
        log.info("No tip generated (Gemini unavailable or failed)")

    log.info("Generating prediction card...")
    card = generate_prediction_card(pred, tip=tip)
    card_path = day_dir / "prediction_card.jpg"
    card.save(card_path, "JPEG", quality=95)
    log.info(f"Card saved: {card_path}")

    caption = build_noon_caption(pred, tip=tip)
    log.info(f"Caption ({len(caption)} chars):\n{caption}")

    if dry_run:
        log.info("Dry run — skipping Instagram post")
        return

    success = post_to_instagram(card_path, caption)
    if success:
        log.info("Prediction card posted to Instagram")
    else:
        log.warning("Failed to post prediction card to Instagram")


def run_photo_post(dry_run: bool = False):
    """Post the evening sunset photo with score overlay."""
    day_dir = _get_today_dir()
    if not day_dir.exists():
        log.error(f"No data directory for today: {day_dir}")
        sys.exit(1)

    pred = _load_latest_prediction(day_dir)
    manifest = _load_manifest(day_dir)
    ai_rating = {
        "ai_score": manifest.get("ai_score"),
        "ratings_count": len(manifest.get("ai_ratings", [])),
        "ratings": manifest.get("ai_ratings", []),
    }

    if not should_post_evening(ai_rating):
        log.info(f"Evening post skipped — AI score {ai_rating.get('ai_score')} below threshold")
        return

    best = select_best_frame(ai_rating, day_dir)
    if not best:
        log.warning("No qualifying sunset frame found")
        return

    log.info(f"Best frame: {best.name} (score {ai_rating['ai_score']})")

    verdict = get_verdict(ai_rating["ai_score"])
    overlaid = overlay_score(best, ai_rating["ai_score"], verdict)
    out_path = day_dir / "sunset_post.jpg"
    overlaid.save(out_path, "JPEG", quality=95)
    log.info(f"Overlaid image saved: {out_path}")

    caption = build_evening_caption(pred, ai_rating)
    log.info(f"Caption ({len(caption)} chars):\n{caption}")

    if dry_run:
        log.info("Dry run — skipping Instagram post")
        return

    success = post_to_instagram(out_path, caption)
    if success:
        log.info("Sunset photo posted to Instagram")
    else:
        log.warning("Failed to post sunset photo to Instagram")


def main():
    parser = argparse.ArgumentParser(description="Post sunset content to Instagram")
    parser.add_argument("--prediction", action="store_true",
                        help="Post noon prediction card")
    parser.add_argument("--photo", action="store_true",
                        help="Post evening sunset photo")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate content without posting to Instagram")
    args = parser.parse_args()

    if not args.prediction and not args.photo:
        parser.error("Specify --prediction or --photo (or both)")

    if args.prediction:
        run_prediction_post(dry_run=args.dry_run)

    if args.photo:
        run_photo_post(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
