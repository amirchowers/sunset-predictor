# Weather Source Upgrade — Implementation Brief

**Date:** 2026-03-17
**Priority:** HIGH — directly impacts prediction accuracy
**Context:** Predicted 6.4/10 for today; actual sunset was a 2/10 (human score). Root cause: Open-Meteo forecast showed 0% cloud cover at all 5 checkpoints while actual conditions were heavy overcast. Competitor [sunset-predictor.com](https://sunset-predictor.com/) (which uses OpenWeather) correctly predicted "Low Quality Sunset" with 100% cloud cover.

---

## Problem

Open-Meteo's cloud forecast has been consistently optimistic. Only 2 days of human calibration data exist, but both show the model over-predicting:

| Date | Predicted | Human | Delta |
|------|-----------|-------|-------|
| 2026-03-16 | 7.6 | 5.5 | +2.1 |
| 2026-03-17 | 6.4 | 2.0 | +4.4 |

The scorer model itself is sound — it correctly maps weather inputs to sunset quality. The data source is the weak link.

---

## Task 1: Add OpenWeather as primary weather source

### Why OpenWeather

- Competitor sunset-predictor.com uses it and correctly predicted today's overcast
- Free tier: 1,000 calls/day via One Call API 3.0, or 60 calls/min on the 5-day forecast endpoint
- Provides cloud layer data (low/mid/high) which the scorer already uses
- API key activation is near-instant now (this was previously a concern in the codebase docs)

### What to build

Create `sunset_predictor/fetcher_openweather.py` (or add a class to `fetcher.py`) that implements the same interface as `OpenMeteoFetcher`:

```python
class OpenWeatherFetcher:
    def __init__(self, api_key: str): ...
    def get_weather_at_sunset(self, lat, lon, sunset_time) -> dict: ...
    def get_air_quality(self, lat, lon) -> dict: ...
    def get_western_sky_weather(self, western_points, sunset_time) -> dict: ...
```

**The return format must match the existing scorer input.** The scorer expects:

```python
# From get_weather_at_sunset:
{
    "clouds": {"all": float},           # total cloud cover %
    "cloud_layers": {                   # optional but preferred
        "low": float,                   # cloud_cover_low %
        "mid": float,                   # cloud_cover_mid %
        "high": float,                  # cloud_cover_high %
    },
    "main": {"humidity": float},        # relative humidity %
    "visibility": float,               # meters
    "weather": [{"id": int, "description": str}],  # OWM-style weather code
    "comfort": {
        "temp_c": float,
        "feels_like_c": float,
        "wind_kmh": float,
        "wind_gusts_kmh": float,
    },
}

# From get_air_quality:
{"list": [{"components": {"pm2_5": float}}]}

# From get_western_sky_weather:
{"near": <weather_dict>, "far": <weather_dict>}
```

### OpenWeather API endpoints to use

**One Call API 3.0** (preferred — 1,000 free calls/day):
```
GET https://api.openweathermap.org/data/3.0/onecall
  ?lat={lat}&lon={lon}&appid={API_KEY}&units=metric
```
Returns `hourly[]` with `clouds`, `humidity`, `visibility`, `weather[].id`, `temp`, `feels_like`, `wind_speed`, `wind_gust`.

Cloud layers are NOT in One Call. For cloud layers, use:

**5-day/3-hour Forecast** (free, unlimited with key):
```
GET https://api.openweathermap.org/data/2.5/forecast
  ?lat={lat}&lon={lon}&appid={API_KEY}&units=metric
```
Returns `list[]` with `clouds.all`. Cloud layers (low/mid/high) are available via `clouds.low`, `clouds.mid`, `clouds.high` in the pro tier only.

**Air Quality** (free):
```
GET https://api.openweathermap.org/data/2.5/air_pollution/forecast
  ?lat={lat}&lon={lon}&appid={API_KEY}
```
Returns `list[].components.pm2_5`.

### Implementation notes

1. **API key:** Add `OPENWEATHER_API_KEY` to `.env` and `.env.example`. The user needs to sign up at [openweathermap.org](https://openweathermap.org/api/) — free tier is sufficient.

2. **Time selection:** OpenWeather returns hourly data. Pick the hour closest to sunset time (same logic as the current Open-Meteo fetcher).

3. **Weather codes:** OpenWeather uses its own weather condition IDs (200–804). The scorer already expects OWM-style IDs because the Open-Meteo fetcher maps WMO codes to OWM codes via `WMO_TO_OWM`. OpenWeather returns native OWM codes, so no mapping needed.

4. **Cloud layers:** OpenWeather free tier may not provide low/mid/high split. If not available, set `has_cloud_layers = False` and the scorer will use `WEIGHTS_LEGACY` (which uses total cloud cover instead). This is fine — total cloud cover alone would have caught today's miss.

5. **Units:** Request `units=metric`. Wind comes back in m/s — multiply by 3.6 for km/h. Visibility is in meters.

6. **Western sky:** Same approach as current: call `get_weather_at_sunset` for the near point (25km along sunset azimuth) and far point (80km along sunset azimuth). That's 3 API calls per prediction (local + near + far) + 1 for air quality = 4 calls. At 5 predictions/day = 20 calls. Well within free tier.

7. **Retry/timeout:** Add `timeout=15` and basic retry (2 attempts) since the current fetcher has no retry and occasionally fails on SSL/timeout.

### How to wire it in

In `daily_sunset.py`, the prediction flow is in `run_prediction()`:

```python
def run_prediction(location):
    sun_info = get_sunset_info(location.lat, location.lon, location.timezone, location.name)
    western_points = get_western_sky_points(location.lat, location.lon, sun_info["azimuth"])

    fetcher = OpenMeteoFetcher()  # ← CHANGE THIS
    weather = fetcher.get_weather_at_sunset(location.lat, location.lon, sun_info["sunset"])
    air_quality = fetcher.get_air_quality(location.lat, location.lon)
    western_sky = fetcher.get_western_sky_weather(western_points, sun_info["sunset"])

    result = calculate_sunset_score(weather, air_quality, western_sky)
    verdict = get_verdict(result["overall"])
    return sun_info, result, verdict
```

Replace `OpenMeteoFetcher()` with `OpenWeatherFetcher(api_key)` where `api_key = os.getenv("OPENWEATHER_API_KEY")`. If no key, fall back to `OpenMeteoFetcher()`.

---

## Task 2: Add competitor benchmark (sunset-predictor.com API)

### What

Pull the competitor's prediction for Tel Aviv alongside each prediction run. Store it in the manifest for calibration comparison.

### Competitor API

- **Docs:** [sunset-predictor.com/api-docs/](https://sunset-predictor.com/api-docs/) (wasn't fetchable at time of writing — check it live)
- **Uses:** OpenWeather as their data source
- **Score system:** 0–100 scale (divide by 10 to compare with our 1–10 scale)
- **Shows:** quality score, confidence level, cloud cover %, humidity %, rain chance

### Implementation

1. Add a function `fetch_competitor_score(lat, lon, date)` that calls their API
2. Store result in manifest under a new field: `competitor_score`
3. Log it: `log.info(f"Competitor score: {competitor_score}")`
4. Don't depend on it for anything — it's purely for calibration/comparison

### Manifest schema addition

```json
{
  "competitor_score": {
    "source": "sunset-predictor.com",
    "score_raw": 13,
    "score_normalized": 1.3,
    "confidence": "high",
    "cloud_cover_pct": 100,
    "fetched_at": "2026-03-17T15:00:00Z"
  }
}
```

---

## Task 3 (optional): Dual-source with confidence

If you have time after Tasks 1–2, add a simple confidence mechanism:

1. Fetch from BOTH Open-Meteo and OpenWeather
2. If they agree on cloud cover (within 20%), high confidence → use average
3. If they disagree (>20% difference), low confidence → use the more pessimistic forecast
4. Log the disagreement for calibration
5. Add `"confidence": "high"|"low"` and `"source_agreement": float` to the prediction entry

This would have caught today: Open-Meteo says 0%, OpenWeather says 100% → massive disagreement → use pessimistic (100%) → score drops to ~2.

---

## Current architecture reference

### Files to modify

| File | Change |
|------|--------|
| `sunset_predictor/fetcher.py` | Add `OpenWeatherFetcher` class (or new file) |
| `daily_sunset.py` | Wire new fetcher, add competitor fetch |
| `.env` / `.env.example` | Add `OPENWEATHER_API_KEY` |
| `calibration_data/*/manifest.json` | New fields for competitor data |

### Files to read (understand before changing)

| File | Why |
|------|-----|
| `sunset_predictor/fetcher.py` | Current Open-Meteo implementation — match the interface |
| `sunset_predictor/scorer.py` | Input format expectations, scoring thresholds |
| `sunset_predictor/sun.py` | Western sky point computation (25km/80km along azimuth) |
| `sunset_predictor/config.py` | Location: Tel Aviv 32.0853, 34.7818, Asia/Jerusalem |
| `daily_sunset.py` | Pipeline flow: predict → tip → notify → post |

### Scorer input contract (DO NOT CHANGE)

The scorer (`calculate_sunset_score`) expects exactly this input shape. Your new fetcher must produce it:

```python
# weather (from get_weather_at_sunset)
weather["clouds"]["all"]                    # float, 0–100
weather["cloud_layers"]["low"]              # float, 0–100 (optional)
weather["cloud_layers"]["mid"]              # float, 0–100 (optional)
weather["cloud_layers"]["high"]             # float, 0–100 (optional)
weather["main"]["humidity"]                 # float, 0–100
weather["visibility"]                       # float, meters
weather["weather"][0]["id"]                 # int, OWM weather code (200–804)
weather["weather"][0]["description"]        # str
weather["comfort"]["temp_c"]               # float
weather["comfort"]["feels_like_c"]         # float
weather["comfort"]["wind_kmh"]             # float
weather["comfort"]["wind_gusts_kmh"]       # float

# air_quality (from get_air_quality)
air_quality["list"][0]["components"]["pm2_5"]  # float

# western_sky (from get_western_sky_weather)
western_sky["near"]                         # same shape as weather
western_sky["far"]                          # same shape as weather
```

### Scoring weights (for context)

| Factor | Weight | What drives it |
|--------|--------|---------------|
| cloud_high | 0.15 | High cirrus clouds (best for color) |
| cloud_low_mid | 0.10 | Low/mid clouds (block sun if too thick) |
| western_near | 0.20 | Cloud cover 25km toward sunset (HIGHEST weight) |
| western_far | 0.10 | Cloud cover 80km toward sunset |
| humidity | 0.10 | Moisture for scattering |
| visibility | 0.10 | Atmospheric clarity |
| air_quality | 0.10 | Aerosol scattering (moderate PM2.5 is good) |
| weather_condition | 0.15 | Rain/storm/clear/overcast code |

### Key scoring thresholds

- **Cloud high:** 20–50% → best (7–10), 0% → 4, >85% → 5
- **Cloud low:** >70% low → 1 (blocks sun)
- **Weather condition:** 800 (clear) → 6, 802 (scattered) → 10 (ideal), 804 (overcast) → check western
- **Verdict cutoffs:** ≥8.0 rare show, ≥6.5 worth plans, ≥5.0 watchable, ≥3.5 blocked, <3.5 skip

---

## Calibration data available

21 days of prediction data (2026-02-25 to 2026-03-18). Only 2 have human scores — both show over-prediction. Full prediction history is in `calibration_data/*/predictions.json` with per-factor scores and raw weather inputs.

---

## Rules

- Python 3.9 — use `Optional[X]` not `X | None`
- `.env` for API keys, `load_dotenv()` at top of `main()` in `daily_sunset.py` (already added)
- All existing tests must pass (`python3 -m pytest tests/test_poster.py`)
- Don't change the scorer model — only the data feeding into it
- Add retry logic to the new fetcher (the current one has none and fails ~30% of the time on flaky connections)
- Log weather source used in each prediction for debugging
