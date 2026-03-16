# TESTING.md

Manual test checklist for the Sunset Predictor MVP.

## Test Environment

- Python 3.9+
- Dependencies installed from `requirements.txt`
- Run from project root:
  `/Users/amir.chowers/Desktop/AI Project /sunset-predictor`

## 1) Prediction Smoke Test

Command:

```bash
python3 main.py
```

Verify:
- Script exits with code 0
- Prints sunset time, score, verdict, and factor breakdown
- No tracebacks

## 2) Snapshot Capture Test

Command:

```bash
python3 capture_sunset.py
```

Verify:
- Creates/uses `calibration_data/YYYY-MM-DD/`
- Writes `prediction.json`
- Runs camera check and captures from live cameras
- Writes `manifest.json`
- At least one `.jpg` saved when cameras are live

## 3) Sunset Window Capture Test (Timed)

Command:

```bash
python3 capture_sunset.py --wait
```

Verify:
- Waits until scheduled offsets
- Attempts captures at `before`, `sunset`, `after_10`, `after_20`
- Resulting images have label suffixes matching offsets

## 4) Backtest Reliability Test

Command:

```bash
python3 backtest.py
```

Verify:
- Writes `backtest_results.csv`
- Prints total scored days and average score
- If any day fails, prints skipped-day count and error summary
- If all rows fail, writes header-only CSV and exits non-zero with failure summary

## 5) Data Quality Spot Check

After any capture run:
- Open latest `calibration_data/YYYY-MM-DD/manifest.json`
- Confirm image paths exist
- Confirm `predicted_score` matches `prediction.json`
- Confirm `actual_score` remains `null` until manually/AI rated

## 6) Camera Discovery Test

Command:

```bash
python3 discover_cameras.py
```

Verify:
- Searches multiple YouTube queries
- Reports working vs. placeholder thumbnails with sizes
- Prints copy-pasteable Camera entries for any new finds

## 7) Camera Liveness Verification

Quick Python check to confirm cameras are serving fresh frames:

```bash
python3 -c "
from sunset_predictor.cameras import get_cameras
import requests, hashlib, time
cams = get_cameras()[:2]
for c in cams:
    r = requests.get(c.image_url, timeout=10)
    print(f'{c.name}: {len(r.content)//1024}KB — {\"OK\" if len(r.content) > c.min_size else \"STALE\"} ')
"
```

For full liveness (proves thumbnails update), grab two frames 5 min apart and compare hashes. Thumbnails update roughly every 5 minutes.

## 8) Daily Pipeline Test (multi-timepoint predictions)

Command:

```bash
python3 daily_sunset.py
```

Verify:
- Exits with code 0
- Creates/appends to `calibration_data/YYYY-MM-DD/predictions.json`
- Each entry has `predicted_at_utc`, `hours_before_sunset`, `score`
- Run a second time and confirm predictions.json has 2 entries

Command (with immediate capture):

```bash
python3 daily_sunset.py --capture --now
```

Verify:
- Captures webcam frames immediately
- Updates `manifest.json` with image list and prediction spread

## 9) Human Rating Test

Command:

```bash
python3 rate_day.py --date YYYY-MM-DD --score 7.0 --notes "test"
```

Verify:
- Updates `manifest.json` with `human_score` and `human_notes`
- Does not overwrite other manifest fields

## 10) Retro Report Test (7-day review with drift)

Command:

```bash
python3 retro_review.py --days 7
```

Verify:
- Generates `calibration_data/retro_7d.csv`
- Generates `calibration_data/retro_7d.md`
- Report includes predicted score, human score (if present), and image references
- When multi-timepoint predictions exist, shows "Prediction Drift" section with per-timepoint scores

## 11) launchd Installation Test

Command:

```bash
bash launchd/install.sh
launchctl list | grep com.sunset
```

Verify:
- Four jobs listed: `com.sunset.morning`, `com.sunset.noon`, `com.sunset.afternoon`, `com.sunset.capture`
- Uninstall cleanly: `bash launchd/uninstall.sh`

## 12) Telegram Notification Test

Command:

```bash
python3 daily_sunset.py --notify
```

Verify:
- Terminal logs show "Telegram: prediction sent"
- Message appears in Telegram from `@Sunsettlvbot` with score, verdict, breakdown, sunset time

## 13) Vision AI Rating Test

Command:

```bash
python3 calibrate.py --date 2026-02-25
```

Verify:
- Rates images via Gemini (primary) or HuggingFace (fallback)
- Logs show "AI score: X/10 (N images rated)"
- `calibration_data/2026-02-25/manifest.json` has `ai_score` set to a number
- `ai_ratings` array has per-image entries with `score` and `reasoning`

## 14) Capture + Vision AI Integration Test

Command:

```bash
python3 daily_sunset.py --capture --now
```

Verify:
- Captures from `ashdod_arches` camera only (1 image)
- If `GEMINI_API_KEY` or `HUGGINGFACE_API_KEY` is set: logs "Rating N images via Vision AI..."
- If neither key is set: logs "No GEMINI_API_KEY or HUGGINGFACE_API_KEY — skipping Vision AI rating"
- `manifest.json` updated with images and (optionally) AI rating

## 15) Instagram Prediction Card Test (Dry Run)

Command:

```bash
python3 post_sunset.py --prediction --dry-run
```

Verify:
- Generates `calibration_data/YYYY-MM-DD/prediction_card.jpg` (1080x1080 JPEG)
- Logs show score, Gemini-generated tip, and caption
- Card has sunset gradient background, score, verdict, and tip text
- Caption under 2200 characters

## 16) Instagram Sunset Photo Test (Dry Run)

Command:

```bash
python3 post_sunset.py --photo --dry-run
```

Verify:
- Selects best-rated frame from today's captures
- Generates `calibration_data/YYYY-MM-DD/sunset_post.jpg` with score overlay badge
- Skips posting if AI score is below 3
- Caption includes predicted vs actual comparison

## 17) Automated Test Suite

Command:

```bash
python3 -m pytest tests/ -v
```

Verify:
- All 225 tests pass
- Tests cover: scorer (132), notifier (24), rater (29), calibrate (10), poster (30)

## Regression Notes

Re-run sections 1 and 4 whenever touching:
- `sunset_predictor/scorer.py`
- `sunset_predictor/fetcher.py`
- `sunset_predictor/sun.py`
- `backtest.py`

Re-run section 2 whenever touching:
- `sunset_predictor/cameras.py`
- `capture_sunset.py`

Re-run section 8 whenever touching:
- `daily_sunset.py`
- `retro_review.py`

