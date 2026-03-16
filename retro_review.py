"""Generate a retro calibration report for recent sunset runs.

Includes multi-timepoint prediction drift when predictions.json exists.

Usage:
    python3 retro_review.py --days 7
"""

import argparse
import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "calibration_data"


def parse_day_dir(day_dir: Path) -> Optional[date]:
    try:
        return datetime.strptime(day_dir.name, "%Y-%m-%d").date()
    except ValueError:
        return None


def read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def resolve_image_path(day_dir: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p
    from_data_dir = DATA_DIR / p
    if from_data_dir.exists():
        return from_data_dir
    return day_dir / p


def load_predictions(day_dir: Path) -> list[dict]:
    """Load multi-timepoint predictions (new format) or fall back to single prediction."""
    multi = read_json(day_dir / "predictions.json")
    if isinstance(multi, list) and multi:
        return multi

    single = read_json(day_dir / "prediction.json")
    if isinstance(single, dict) and "score" in single:
        return [single]

    return []


def collect_rows(days: int) -> list[dict]:
    today = date.today()
    start_date = today - timedelta(days=days - 1)
    rows = []

    if not DATA_DIR.exists():
        return rows

    for day_dir in sorted(DATA_DIR.iterdir()):
        if not day_dir.is_dir():
            continue
        day_date = parse_day_dir(day_dir)
        if day_date is None or day_date < start_date or day_date > today:
            continue

        manifest = read_json(day_dir / "manifest.json") or {}
        predictions = load_predictions(day_dir)

        # Latest prediction is the "final" predicted score
        latest_score = predictions[-1].get("score") if predictions else None
        predicted = manifest.get("predicted_score", latest_score)

        human = manifest.get("human_score")
        if human is None:
            human = manifest.get("actual_score")
        delta = None
        if predicted is not None and human is not None:
            delta = round(float(human) - float(predicted), 1)

        # Prediction drift across timepoints
        drift_entries = []
        for p in predictions:
            drift_entries.append({
                "time": p.get("predicted_at_local", p.get("predicted_at_utc", "?")),
                "hours_before": p.get("hours_before_sunset"),
                "score": p.get("score"),
            })

        earliest_score = predictions[0].get("score") if predictions else None
        score_spread = None
        if earliest_score is not None and latest_score is not None and len(predictions) > 1:
            score_spread = round(latest_score - earliest_score, 1)

        # Images
        image_paths = manifest.get("images", [])
        existing_images = []
        missing_images = []
        for raw in image_paths:
            resolved = resolve_image_path(day_dir, raw)
            if resolved.exists():
                existing_images.append(str(resolved))
            else:
                missing_images.append(str(raw))

        verdict = ""
        if predictions:
            verdict = predictions[-1].get("verdict", "")
        if not verdict:
            single = read_json(day_dir / "prediction.json")
            if isinstance(single, dict):
                verdict = single.get("verdict", "")

        rows.append({
            "date": day_dir.name,
            "predicted_score": predicted,
            "human_score": human,
            "delta_human_minus_predicted": delta,
            "prediction_count": len(predictions),
            "earliest_score": earliest_score,
            "latest_score": latest_score,
            "score_spread": score_spread,
            "drift_entries": drift_entries,
            "verdict": verdict,
            "images_found": len(existing_images),
            "images_missing": len(missing_images),
            "images": existing_images,
            "missing_image_refs": missing_images,
            "human_notes": manifest.get("human_notes", ""),
            "notes": manifest.get("notes", ""),
        })

    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def write_csv(rows: list[dict], output_csv: Path) -> None:
    fields = [
        "date",
        "predicted_score",
        "human_score",
        "delta_human_minus_predicted",
        "prediction_count",
        "earliest_score",
        "latest_score",
        "score_spread",
        "verdict",
        "images_found",
        "images_missing",
        "human_notes",
        "notes",
    ]
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_markdown(rows: list[dict], output_md: Path, days: int) -> None:
    lines = []
    lines.append(f"# Sunset Calibration Retro ({days} days)")
    lines.append("")
    if not rows:
        lines.append("No calibration runs found in selected period.")
        output_md.write_text("\n".join(lines) + "\n")
        return

    lines.append("| Date | Final Pred | Human | Delta | Predictions | Earliest | Spread | Images | Verdict |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in rows:
        pred = "" if r["predicted_score"] is None else r["predicted_score"]
        human = "" if r["human_score"] is None else r["human_score"]
        delta = "" if r["delta_human_minus_predicted"] is None else r["delta_human_minus_predicted"]
        earliest = "" if r["earliest_score"] is None else r["earliest_score"]
        spread = "" if r["score_spread"] is None else r["score_spread"]
        lines.append(
            f"| {r['date']} | {pred} | {human} | {delta} "
            f"| {r['prediction_count']} | {earliest} | {spread} "
            f"| {r['images_found']} | {r['verdict']} |"
        )

    # Prediction drift detail
    has_drift = any(len(r["drift_entries"]) > 1 for r in rows)
    if has_drift:
        lines.append("")
        lines.append("## Prediction Drift (score at each timepoint)")
        lines.append("")
        for r in rows:
            if len(r["drift_entries"]) <= 1:
                continue
            lines.append(f"### {r['date']}")
            lines.append("| Time | Hours Before | Score |")
            lines.append("|---|---:|---:|")
            for d in r["drift_entries"]:
                hrs = "" if d["hours_before"] is None else d["hours_before"]
                lines.append(f"| {d['time']} | {hrs} | {d['score']} |")
            if r["human_score"] is not None:
                lines.append(f"| **Human rating** | — | **{r['human_score']}** |")
            lines.append("")

    # Image references
    lines.append("## Image References")
    lines.append("")
    for r in rows:
        lines.append(f"### {r['date']}")
        if r["images"]:
            for img in r["images"]:
                lines.append(f"- {img}")
        else:
            lines.append("- No images found")
        if r["missing_image_refs"]:
            lines.append("- Missing image refs:")
            for missing in r["missing_image_refs"]:
                lines.append(f"  - {missing}")
        if r["human_notes"]:
            lines.append(f"- Human notes: {r['human_notes']}")
        if r["notes"]:
            lines.append(f"- Notes: {r['notes']}")
        lines.append("")

    output_md.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate retro calibration review")
    parser.add_argument("--days", type=int, default=7, help="How many recent days to include")
    parser.add_argument("--unrated", action="store_true", help="Show only days without a human score")
    args = parser.parse_args()

    if args.days < 1:
        raise SystemExit("--days must be >= 1")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = collect_rows(args.days)

    if args.unrated:
        rows = [r for r in rows if r["human_score"] is None and r["images_found"] > 0]

    output_csv = DATA_DIR / f"retro_{args.days}d.csv"
    output_md = DATA_DIR / f"retro_{args.days}d.md"

    write_csv(rows, output_csv)
    write_markdown(rows, output_md, args.days)

    print(f"Retro rows: {len(rows)}")
    print(f"CSV: {output_csv}")
    print(f"MD:  {output_md}")


if __name__ == "__main__":
    main()
