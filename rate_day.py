"""Set human rating for a given sunset calibration day.

Usage examples:
    python3 rate_day.py --date 2026-02-25 --score 7.5
    python3 rate_day.py --date 2026-02-25 --score 7.5 --notes "great gap sunset"
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "calibration_data"


def load_manifest(day_dir: Path) -> dict:
    path = day_dir / "manifest.json"
    if not path.exists():
        raise SystemExit(f"manifest.json not found for {day_dir.name}")
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        raise SystemExit(f"Failed to parse manifest.json: {exc}")


def save_manifest(day_dir: Path, manifest: dict) -> None:
    path = day_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


def parse_date_str(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise SystemExit("Date must be in YYYY-MM-DD format")
    return dt.date().isoformat()


def main():
    parser = argparse.ArgumentParser(description="Set human rating for a sunset day")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD (must match folder name)")
    parser.add_argument("--score", type=float, required=True, help="Human rating 1–10")
    parser.add_argument("--notes", type=str, default="", help="Optional human notes about this sunset")
    args = parser.parse_args()

    if not (0.0 <= args.score <= 10.0):
        raise SystemExit("--score must be between 0 and 10")

    norm_date = parse_date_str(args.date)
    day_dir = DATA_DIR / norm_date
    if not day_dir.exists():
        raise SystemExit(f"No calibration folder for {norm_date} under {DATA_DIR}")

    manifest = load_manifest(day_dir)

    manifest["human_score"] = round(float(args.score), 1)
    if args.notes:
        manifest["human_notes"] = args.notes

    save_manifest(day_dir, manifest)

    print(f"Updated {norm_date}: human_score={manifest['human_score']}, notes='{manifest.get('human_notes','')}'")


if __name__ == "__main__":
    main()

