# Sunset Predictor — Product Documentation

**Status:** MVP (Tel Aviv / Israeli coast)
**Last updated:** February 2026

---

## What Is This?

A system that predicts how beautiful today's sunset will be, scored 1–10. It answers a simple question: **"Is tonight's sunset worth going to the beach for?"**

Currently focused on Tel Aviv and the Israeli Mediterranean coast. Built to be extensible to any location, and eventually to power an app, website, or automated Instagram account.

---

## How It Works (High Level)

Every day, the system:

1. **Calculates the exact sunset time and direction** for the location
2. **Fetches weather data** at sunset time — not just overhead, but specifically in the direction of the sunset
3. **Scores 8 atmospheric factors** that determine sunset quality
4. **Produces a 1–10 score and a human-readable verdict**
5. **Optionally captures webcam frames** around sunset for model calibration

---

## The Scoring Model

### Core Insight

A beautiful sunset isn't just about "clear skies." The best sunsets actually need some clouds — specifically, **high-altitude clouds** (cirrus, 6km+) that catch and scatter light into vivid colors. Meanwhile, low clouds at the horizon **block** the sun entirely.

The model captures this by scoring 8 independent factors and combining them with a weighted average.

### Scoring Factors

| Factor | Weight | What It Measures | Sweet Spot |
|--------|--------|-----------------|------------|
| **High clouds** | 15% | Cirrus clouds (6km+) — the "color canvas" | 20–50% coverage is ideal |
| **Low/mid clouds** | 10% | Clouds below 6km — these block, not beautify | Lower is better |
| **Western sky (near)** | 20% | Cloud cover 25km toward the sunset — is the horizon blocked? | 25–50% scattered clouds |
| **Western sky (far)** | 10% | Cloud cover 80km toward the sunset — distant color canvas | 20–50% coverage |
| **Humidity** | 10% | Moisture in the air | Below 50% is best |
| **Visibility** | 10% | How far you can see | 10km+ is ideal |
| **Air quality (PM2.5)** | 10% | Particulate matter — moderate aerosols actually help | 15–35 μg/m³ enhances color |
| **Weather condition** | 15% | Rain, fog, thunderstorm vs. clear/scattered | Scattered/broken clouds are best |

Each factor is scored independently on a 1–10 scale, then combined using the weights above.

### Key Scoring Logic

**Clouds by altitude matter more than total cloud cover:**
- High clouds (cirrus) at 20–50% = 10/10 — these are the sunset's best friend
- Low clouds above 70% = 1/10 — they sit right at the horizon and block everything

**The western sky is checked separately from overhead:**
- The system calculates the exact compass direction of the sunset (azimuth)
- It checks weather conditions at two points along that bearing:
  - **Near-west (25km out):** Will something block the sun right at the horizon?
  - **Far-west (80km out):** Are there clouds out there to catch the light?

**"Gap sunset" detection:**
- If overhead conditions say "overcast" but the western horizon has gaps (< 50% clouds), the score gets a boost
- This captures the phenomenon where the sun breaks through a gap right at the waterline

**Air quality has a non-obvious curve:**
- Very clean air (PM2.5 < 5) actually scores only 5/10 — sunsets need *some* particles to scatter light
- Moderate pollution (15–35) scores highest — it enhances reds and oranges
- Heavy pollution (> 55) kills visibility and scores low

### Score Thresholds

| Score | Verdict | What to Expect |
|-------|---------|---------------|
| **8.0+** | "Tell your friends — rare show" | Sky changes colors for 20+ minutes, both east and west. Happens ~8 times/year |
| **6.5–7.9** | "Worth making plans for" | Clear sun touching water, good orange/red tones. ~30 times/year |
| **5.0–6.4** | "Watchable — sun meets the sea" | You can see the sun set, pleasant but not dramatic |
| **3.5–4.9** | "Probably blocked or dull" | Clouds or haze will likely obscure the view |
| **Below 3.5** | "Skip it" | Rain, heavy overcast, or fog. Stay home |

### Comfort Warnings

The system also flags conditions that affect the experience of *watching* the sunset:

- **Very windy** (40+ km/h): Wind and sand may ruin it
- **Windy** (25+ km/h): Noticeable wind
- **Cold** (feels like < 8°C): Dress warm
- **Cool** (feels like < 15°C): Bring a layer

---

## Data Sources

### Weather & Atmospheric Data: Open-Meteo

**API:** `api.open-meteo.com` (free, no API key required)

Data fetched at the hour closest to sunset:
- Cloud cover: total, low (0–2km), mid (2–6km), high (6km+)
- Humidity, visibility, weather condition code
- Wind speed, gusts, temperature, feels-like temperature

The system makes **3 weather API calls per prediction:**
1. At the user's location (overhead conditions)
2. At 25km along the sunset bearing (near-west horizon check)
3. At 80km along the sunset bearing (far-west cloud canvas)

### Air Quality: Open-Meteo Air Quality API

**API:** `air-quality-api.open-meteo.com` (free, no API key)

Fetches PM2.5 particulate matter readings for the location.

### Astronomical Data: Astral Library

Calculates locally (no API call):
- Exact sunset time for the date and location
- Sunset azimuth (compass bearing where the sun sets)
- Sunrise time

The azimuth is critical — it determines the direction to check for western sky conditions. In Tel Aviv in February, the sun sets roughly WSW (~255°). In summer, it shifts north toward WNW (~290°).

---

## Automated Calibration Pipeline

### Problem

The scoring model uses "educated guess" weights and thresholds. To improve it, we need ground truth: **what did the sunset actually look like?** Going to the beach every day isn't scalable.

### Solution: Live Webcam Capture

The system captures frames from live YouTube beach webcams around sunset time, then (eventually) feeds them to a Vision AI to generate an objective quality rating.

### How the webcam capture works

1. **Source:** YouTube live streams from Ashdod beach cameras (same Mediterranean coastline, ~30km south of Tel Aviv)
2. **Technique:** YouTube serves a live-updating JPEG thumbnail for every active live stream at a predictable URL. No API key, no video download, no browser automation — just a simple image download
3. **Update frequency:** Thumbnails refresh approximately every 5 minutes
4. **Resolution:** 640x480 (SD) — sufficient for sky color assessment

### Current Camera Fleet

| Camera | Direction | YouTube Stream |
|--------|-----------|---------------|
| Ashdod Arches Beach | West | Live 24/7 |
| Ashdod Mei Ami Beach | West | Live 24/7 |
| Ashdod Zevulun Beach | West-NW | Live 24/7 |
| Ashdod Metzuda Beach | West | Live 24/7 |
| Ashdod Lido Beach | West | Live 24/7 |
| Israel Multi-cam (grid) | Multiple | Live 24/7, includes Tel Aviv |

### Capture Modes

- **Instant snapshot:** Captures one frame from each camera right now
- **Sunset window (--wait):** Automatically waits and captures at 4 time points:
  - 10 minutes before sunset
  - At sunset
  - 10 minutes after
  - 20 minutes after

### Data Output

Each day's capture creates a folder (`calibration_data/YYYY-MM-DD/`) containing:
- `prediction.json` — the model's prediction and all raw data
- `manifest.json` — list of images, predicted score, space for actual score
- `*.jpg` — captured webcam frames

### Calibration Loop (Planned)

1. Capture frames daily around sunset
2. Vision AI (GPT-4V or Claude) rates the sunset 1–10 based on images
3. Compare AI rating to model's prediction
4. Identify which factors the model got wrong
5. Adjust weights and thresholds
6. Repeat

---

## Architecture

### Components

| Component | What It Does |
|-----------|-------------|
| `config.py` | Location settings (lat/lon, timezone). Currently: Tel Aviv |
| `sun.py` | Sunset time, azimuth, and western sky coordinate calculation |
| `fetcher.py` | Pulls weather + air quality from Open-Meteo APIs |
| `scorer.py` | The scoring engine — all factor scoring and weighting |
| `formatter.py` | Formats and displays the prediction output |
| `cameras.py` | Registry of live webcams and their URLs |
| `main.py` | Run a prediction for today's sunset |
| `capture_sunset.py` | Full pipeline: predict + capture webcam frames |
| `backtest.py` | Run the model against a year of historical weather data |
| `discover_cameras.py` | Search YouTube for new live webcams |

### Tech Stack

- **Language:** Python 3
- **Weather API:** Open-Meteo (free, no key)
- **Astronomy:** Astral library (local calculation)
- **Webcam capture:** YouTube live thumbnails (HTTP GET for a JPEG)
- **Storage:** Local filesystem (JSON + JPEG)

### Extensibility

The system is designed to be extended:
- **New locations:** Add a `Location` object in `config.py` (lat, lon, timezone)
- **New cameras:** Add a YouTube video ID to `cameras.py`
- **New scoring factors:** Add a scoring function and weight in `scorer.py`
- **Output channels:** The prediction result is a plain dict — easy to feed into an API, Telegram bot, Instagram post generator, etc.

---

## Backtesting

A backtesting script runs the scoring model against a full year of historical weather data (via Open-Meteo's archive API). This reveals:

- **Score distribution:** How often does the model predict each score tier?
- **High-scoring days:** Which dates scored 8+ and why?
- **Seasonal patterns:** Do certain months produce more spectacular sunsets?
- **Model sanity:** Does the model flag rainy days as bad and scattered-cloud days as great?

Backtesting uses the same scoring engine as live predictions, but with historical hourly data instead of forecasts.

---

## What's Next

### Short-term
- [ ] **Vision AI integration:** Automatically rate captured webcam frames using GPT-4V or Claude
- [ ] **Calibration feedback loop:** Compare predictions vs. actual ratings, tune weights
- [ ] **Find Tel Aviv webcams:** Currently using Ashdod (same coast, same conditions) — ideal to also have Tel Aviv cameras

### Medium-term
- [ ] **Daily automated runs:** Cron job or scheduled task to capture every sunset
- [ ] **Telegram/WhatsApp bot:** "Tonight's sunset: 7.2/10 — Worth making plans for"
- [ ] **Multi-location support:** Haifa, Eilat, other coastal cities

### Long-term
- [ ] **Instagram automation:** Post the best sunset predictions + webcam captures with an engaged community
- [ ] **Web app / mobile app:** Interactive sunset forecast for any location
- [ ] **Community photos:** Let followers upload their sunset photos, create a calibration flywheel

---

## Key Decisions & Rationale

| Decision | Why |
|----------|-----|
| Open-Meteo over OpenWeatherMap | Free, no API key, better cloud layer data (low/mid/high) |
| Check weather in the sunset *direction*, not just overhead | A clear sky overhead means nothing if there's a wall of clouds where the sun is setting |
| SD-resolution YouTube thumbnails | They work, they're free, they update every ~5 min. Good enough for Vision AI to judge sunset quality |
| Ashdod cameras instead of Tel Aviv | These are the only reliable 24/7 west-facing beach cams we found that are actually live on YouTube. Same coastline, same atmospheric conditions |
| Weighted average scoring (not ML) | Interpretable, debuggable, easy to tune manually before we have enough ground truth data for ML |
| PM2.5 as a scoring factor with a curve | Counter-intuitive but scientifically real: moderate aerosols enhance sunset colors via Rayleigh scattering |
