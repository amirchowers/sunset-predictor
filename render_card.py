"""Generate sample prediction cards using the new design system.

Usage:
    python3 render_card.py                        # both formats, sample data
    python3 render_card.py --feed                  # feed card only
    python3 render_card.py --story                 # story card only
    python3 render_card.py --score 2.8 --verdict "Skip it" --no-tip
    python3 render_card.py --json prediction.json  # load prediction from file
"""

import argparse
import json
import sys
from pathlib import Path

from sunset_predictor.renderer import render_feed_card, render_story_card

SAMPLE_PREDICTION = {
    "score": 7.6,
    "verdict": "Worth making plans for",
    "sunset_local": "17:49",
    "city": "TEL AVIV",
    "scores": {
        "cloud_high": 8.0,
        "cloud_low_mid": 7.0,
        "western_near": 9.0,
        "western_far": 6.0,
        "humidity": 6.0,
        "visibility": 10.0,
        "air_quality": 7.0,
        "weather_condition": 8.0,
    },
    "raw": {"condition": "scattered clouds"},
    "comfort": {"temp_c": 22.0, "wind_kmh": 12.0},
}

SAMPLE_TIP = "Grab a cold Goldstar and find a bench on the Tayelet."

OUTPUT_DIR = Path(__file__).parent / "output"


def main():
    parser = argparse.ArgumentParser(description="Generate sample prediction cards")
    parser.add_argument("--feed", action="store_true", help="Generate feed card only")
    parser.add_argument("--story", action="store_true", help="Generate story card only")
    parser.add_argument("--score", type=float, help="Override score value")
    parser.add_argument("--verdict", type=str, help="Override verdict text")
    parser.add_argument("--tip", type=str, help="Override tip text")
    parser.add_argument("--no-tip", action="store_true", help="Omit the tip section")
    parser.add_argument("--json", type=str, help="Load prediction from JSON file")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    both = not args.feed and not args.story

    if args.json:
        with open(args.json) as f:
            pred = json.load(f)
    else:
        pred = SAMPLE_PREDICTION.copy()

    if args.score is not None:
        pred["score"] = args.score
    if args.verdict:
        pred["verdict"] = args.verdict

    tip = None if args.no_tip else (args.tip or SAMPLE_TIP)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.feed or both:
        print(f"Rendering feed card (score={pred['score']})...")
        img = render_feed_card(pred, tip=tip)
        path = out / "sample_feed.jpg"
        img.save(path, "JPEG", quality=95)
        print(f"  -> {path}  ({img.size[0]}x{img.size[1]})")

    if args.story or both:
        print(f"Rendering story card (score={pred['score']})...")
        img = render_story_card(pred, tip=tip)
        path = out / "sample_story.jpg"
        img.save(path, "JPEG", quality=95)
        print(f"  -> {path}  ({img.size[0]}x{img.size[1]})")

    print("Done.")


if __name__ == "__main__":
    main()
