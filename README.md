# Sunset Predictor

Predicts how beautiful tonight's sunset will be (1-10), then optionally captures webcam frames for calibration.

## Current Status

MVP is working for Tel Aviv / Israeli coast.

**What works now**
- Forecast-based sunset prediction with weighted 8-factor scoring
- Sunset azimuth-aware western sky checks (near/far points)
- Webcam frame capture around sunset (Ashdod Arches beach cam)
- **Vision AI calibration loop** — Gemini 2.5 Flash primary, HuggingFace GLM-4.5V fallback
- **Telegram daily notification** at noon via `@Sunsettlvbot`
- **Batch calibration** script (`calibrate.py`) to rate historical images
- Historical backtest to CSV
- **Daily automation pipeline** (`daily_sunset.py`) with 4 launchd jobs
- **Human rating CLI** (`rate_day.py`) for frictionless calibration input

**First calibration result (2026-02-25)**
- Predicted: 6.8, AI (sunset-window): 4.2-6.5, Human: 6.0
- Arches camera sunset scores (6.0-6.5) closely match human rating

**Next**
- GitHub repo + portfolio README (Phase 4)

## Quick Start

### 1) Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run a prediction

```bash
python3 main.py
```

### 3) Capture webcam snapshots now

```bash
python3 capture_sunset.py
```

### 4) Capture full sunset window (-10, 0, +10, +20)

```bash
python3 capture_sunset.py --wait
```

### 5) Run backtest

```bash
python3 backtest.py
```

Output: `calibration_data/backtest_results.csv`

### 6) Daily automated pipeline (multi-timepoint predictions + capture)

```bash
python3 daily_sunset.py                  # log a prediction now
python3 daily_sunset.py --notify         # log prediction + send to Telegram
python3 daily_sunset.py --capture        # log prediction + capture at sunset window
python3 daily_sunset.py --capture --now  # log prediction + capture immediately
```

Each call appends a timestamped entry to `calibration_data/YYYY-MM-DD/predictions.json`.

### 7) Install daily automation (launchd)

```bash
bash launchd/install.sh    # install 4 scheduled jobs
bash launchd/uninstall.sh  # remove them
```

Schedules: 08:00 (morning prediction), 12:00 (noon prediction + Telegram), 14:00 (afternoon prediction), 16:00 (capture job, waits for sunset).

### 7b) Batch-rate historical images with Vision AI

```bash
python3 calibrate.py --date 2026-02-25
```

### 8) Rate a day's sunset

```bash
python3 rate_day.py --date 2026-02-25 --score 7.5 --notes "great gap sunset"
```

### 9) Generate 7-day calibration retro (scores + drift + image refs)

```bash
python3 retro_review.py --days 7
```

Outputs:
- `calibration_data/retro_7d.csv`
- `calibration_data/retro_7d.md` (includes prediction drift table when multi-timepoint data exists)

## Project Layout

- `main.py` — prediction entrypoint
- `daily_sunset.py` — automated daily pipeline (predict + capture + rate + notify)
- `calibrate.py` — batch Vision AI rating for historical images
- `capture_sunset.py` — legacy prediction + webcam capture
- `backtest.py` — historical scoring backtest
- `rate_day.py` — CLI to set human score for a day
- `retro_review.py` — 7-day calibration retro report with drift
- `discover_cameras.py` — search YouTube for new live Israeli webcams
- `sunset_predictor/scorer.py` — 8-factor scoring model + verdicts
- `sunset_predictor/rater.py` — Vision AI rating (Gemini + HuggingFace fallback)
- `sunset_predictor/notifier.py` — Telegram notification
- `sunset_predictor/cameras.py` — webcam registry (Ashdod Arches)
- `sunset_predictor/fetcher.py` — Open-Meteo data fetches
- `sunset_predictor/sun.py` — sunset time, azimuth, western points
- `sunset_predictor/config.py` — location config
- `sunset_predictor/formatter.py` — CLI output formatting
- `launchd/` — macOS launchd plists + install/uninstall scripts
- `calibration_data/YYYY-MM-DD/` — predictions + images + manifest
- `tests/` — 195 pytest tests (scorer, notifier, rater, calibrate)

## Known Limitations

- Camera pre-check is size-based, not freshness-based.
- YouTube live thumbnails update every ~5 minutes (not real-time video).
- Gemini 2.5 Flash free tier: 5 RPM / 20 RPD — fine for daily 4-image flow, too tight for large batch runs.

## Source Docs

- Product doc: `docs/product_doc.md`
- Spec: `docs/spec.md`
- Implementation plan: `docs/plan.md`

