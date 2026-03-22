# Sunset Predictor -- Implementation Plan

Full spec: `docs/spec.md` (same directory as this file)

## Open Questions

- **HuggingFace model choice:** BLIP-2 and LLaVA are both viable for the Vision AI fallback. The agent should web-search for which HuggingFace Inference API models currently support free image-to-text with structured output (JSON score) and pick the best fit at implementation time.

---

## Tasks

### Phase 0: Verify Foundation ✅
- ✅ Confirm existing pipeline runs: `python3 main.py` and `python3 daily_sunset.py` both exit 0
- ✅ Confirm `notifier.py` imports cleanly

### Phase 0.5: Test Infrastructure + Scorer Tests (TDD Retrofit) ✅
- ✅ Install `pytest`, add to `requirements.txt`
- ✅ Create `tests/` directory with `conftest.py`
- ✅ Write tests for `scorer.py` threshold functions (all 8 scoring functions)
- ✅ Write tests for `scorer.py` weighted scoring and verdicts
- ✅ Write tests for `notifier.py` message formatting
- ✅ Verify all tests pass: `python3 -m pytest tests/ -v` (156 passed)

### Phase 1: Telegram Notification (End to End) ✅
- ✅ MANUAL: Create Telegram bot (@Sunsettlvbot) and get credentials
- ✅ Update `launchd/com.sunset.noon.plist` to pass `--notify` flag
- ✅ Reinstall launchd jobs (all 4 loaded)
- ✅ Test end-to-end delivery with `python3 daily_sunset.py --notify` (message received on Telegram)

### Phase 2: Vision AI Calibration Loop ✅
- ✅ Add HuggingFace fallback to `sunset_predictor/rater.py` (GLM-4.5V via HF auto-router)
- ✅ Fix Gemini: upgraded from deprecated `gemini-2.0-flash` (zero quota) to `gemini-2.5-flash` (5 RPM / 20 RPD free)
- ✅ Wire `rate_images_if_possible()` into the capture flow in `daily_sunset.py`
- ✅ Create `calibrate.py` standalone batch rating script
- ✅ Run rater on existing calibration images (2026-02-25: arches sunset scores 6.0-6.5 vs human 6.0)
- ✅ Camera fleet reduced to `ashdod_arches` only (4 imgs/day, fits within Gemini free tier)
- ✅ No new dependencies needed (HuggingFace called via raw `requests`)

### Phase 3: Light Cleanup ✅
- ✅ Remove dead `OPENWEATHERMAP_API_KEY` from `.env` and `config.py`
- ✅ Remove `capture_sunset.py --rate` stub (redundant with `calibrate.py` and `daily_sunset.py --capture`)
- ✅ Update `README.md` to reflect current reality (4 jobs, correct times, new features)
- ✅ Update `TESTING.md` to match (4 jobs, Telegram test, Vision AI test, Python 3.9)

### Phase 4: GitHub Repo + Future Vision ✅
- ✅ Create `.gitignore`
- ✅ `git init` and initial commit
- ✅ Rewrite `README.md` as portfolio-grade (architecture diagram, scoring explanation, setup guide)
- ✅ Create `calibration_data/example/` with one sanitized sample day
- ✅ Write `docs/future_vision.md`
- ✅ Push to GitHub

### Phase 5: Card Quality — Drivers Fix + Renderer Tests ✅
- ✅ Extract shared `FACTOR_LABELS` / `FACTOR_LABELS_LOW` to `scorer.py` (DRY — remove duplication from renderer.py + poster.py)
- ✅ Fix `_top_drivers()` in `renderer.py`: for overall score < 5.0, sort ascending and use negative phrasing
- ✅ Fix `_top_factors()` in `poster.py`: same logic for caption "Why:" line
- ✅ Add tests for `_top_drivers` / `_top_factors` — high score (positive phrasing) and low score (negative phrasing)
- ✅ Add tests for `renderer._lerp_color` — boundary values (1.0, 10.0), mid-values, between anchors
- ✅ Add tests for `renderer._format_score` — integers strip ".0", fractional keep one decimal
- ✅ Add tests for `renderer._tracking` — zero returns "normal", non-zero returns px value
- ✅ Fix `render_card.py`: auto-derive verdict from score via `get_verdict()` when --score is used without --verdict
- ✅ Verify: `python3 -m pytest tests/ -v` — 253 passed, `python3 main.py` and `python3 daily_sunset.py` exit 0

### Phase 6: OpenWeather Integration
☐ Create `OpenWeatherFetcher` class matching `OpenMeteoFetcher` interface (same return format for scorer)
☐ Add `OPENWEATHER_API_KEY` to `.env.example`
☐ Wire into `daily_sunset.py`: use OpenWeather when key present, fall back to Open-Meteo
☐ Add retry logic (2 attempts, 15s timeout)
☐ Log weather source used in each prediction
☐ Add competitor benchmark fetch (sunset-predictor.com API) — store in manifest, no dependency
☐ Tests for new fetcher: response mapping, fallback logic, retry behavior
☐ Verify: predictions run with both sources, existing tests pass

### Phase 7: Complete Renderer Migration
☐ Wire `renderer.render_feed_card` into `post_sunset.py --prediction` (replace Pillow `generate_prediction_card`)
☐ Port evening photo overlay badge from Pillow to renderer
☐ Bundle local Inter `.woff2` font files for offline/deterministic renders
☐ Update tests: `test_poster.py` card generation tests should use renderer
☐ Verify: `post_sunset.py --prediction --dry-run` and `post_sunset.py --photo --dry-run` produce correct output

---

## Phase 0: Verify Foundation

**Goal:** Confirm the existing codebase works before changing anything.

**Affected Files:** None (read-only)

**Steps:**
- Run `python3 main.py` from the project root -- should print a prediction with score and exit 0
- Run `python3 daily_sunset.py` -- should append to today's `predictions.json` and exit 0
- Run `python3 -c "from sunset_predictor.notifier import send_prediction; print('OK')"` -- should print OK

**Done means:** All three commands exit 0 with no tracebacks.

---

## Phase 0.5: Test Infrastructure + Scorer Tests (TDD Retrofit)

**Goal:** Establish test infrastructure and retrofit tests on the core scoring engine. All new code from here on follows TDD (failing test first).

**Affected Files:**
- `requirements.txt` -- add `pytest`
- `tests/__init__.py` (new) -- empty
- `tests/conftest.py` (new) -- shared fixtures (sample weather data, air quality data, western sky data)
- `tests/test_scorer.py` (new) -- tests for all 8 scoring functions, weighted scoring, and verdicts
- `tests/test_notifier.py` (new) -- tests for message formatting and comfort warnings

**What to test in `scorer.py`:**
- Each threshold function at boundary values (e.g., `_score_cloud_high` at 0%, 5%, 20%, 50%, 70%, 85%, 100%)
- `calculate_sunset_score` with known inputs producing a known weighted result
- `get_verdict` at each threshold boundary (3.5, 5.0, 6.5, 8.0)
- Both code paths: with `cloud_layers` (8-factor) and without (legacy 7-factor)

**What to test in `notifier.py`:**
- `format_message` produces expected structure (score bar, verdict, factor breakdown)
- `_comfort_warnings` returns correct warnings at threshold boundaries
- `_score_bar` renders correctly at 0, 5, 10

**Done means:** `python3 -m pytest tests/ -v` shows all tests passing with 0 failures.

**Test it:**
1. Run `python3 -m pytest tests/ -v`
2. Verify each test function has a descriptive name
3. Verify scorer tests cover boundary values for all 8 factors

---

## Phase 1: Telegram Notification (End to End)

**Goal:** Get a real sunset prediction delivered to Telegram. This is the moment the project becomes a product.

**Affected Files:**
- `.env` -- add bot token and chat_id values
- `launchd/com.sunset.noon.plist` -- add `--notify` to ProgramArguments
- `launchd/install.sh` -- no changes needed (it already copies all plists)

**MANUAL prerequisite (for the user):**
1. Open Telegram, message `@BotFather`
2. Send `/newbot`, follow prompts, copy the token
3. Send any message to your new bot
4. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser
5. Find `"chat":{"id":XXXXXXX}` in the response -- that's your chat_id
6. Paste both values into `.env`

**Agent work:**
- Update `launchd/com.sunset.noon.plist`: add `--notify` as a third string in the ProgramArguments array
- Reinstall launchd jobs: `bash launchd/uninstall.sh && bash launchd/install.sh`

**Done means:** Running `python3 daily_sunset.py --notify` sends a message to Telegram with today's prediction.

**Test it:**
1. Run `python3 daily_sunset.py --notify`
2. Check Telegram -- message should appear with score, verdict, breakdown, sunset time
3. Check terminal logs -- should show "Telegram: prediction sent"

---

## Phase 2: Vision AI Calibration Loop

**Goal:** Close the predict-capture-rate feedback loop. Gemini as primary, HuggingFace as fallback so it always works.

**Affected Files:**
- `sunset_predictor/rater.py` -- add `rate_single_image_huggingface()` fallback function; modify `rate_single_image()` to try Gemini first, catch quota/auth errors, fall back to HuggingFace
- `daily_sunset.py` -- call `rate_images_if_possible()` after capture and pass its result to `save_manifest()`
- `calibrate.py` (new) -- standalone script that takes `--date YYYY-MM-DD` (default: today), loads images from that day's `calibration_data/` folder, runs the rater, writes AI score to `manifest.json`
- `requirements.txt` -- add `huggingface-hub` if needed for the Inference API (or use raw `requests` to avoid the dep)

**Key design decisions:**
- Prefer using `requests` directly to call HuggingFace Inference API to avoid adding `huggingface-hub` as a dependency (YAGNI + minimize deps)
- The HuggingFace fallback should use the same `RATING_PROMPT` and return the same `{score, reasoning}` structure
- `calibrate.py` should be a simple CLI script, not a module -- it's a tool you run manually or could schedule

**TDD requirement:** All new code in this phase must follow TDD. Write failing tests first for:
- `tests/test_rater.py` -- response parsing (valid JSON, malformed JSON, markdown-wrapped JSON), fallback logic (Gemini fails -> HuggingFace called), score aggregation
- `tests/test_calibrate.py` -- manifest reading/writing, date parsing, image path resolution

**Done means:**
- `calibrate.py --date 2026-02-25` rates existing images and writes `ai_score` into that day's `manifest.json`
- The daily capture flow (`daily_sunset.py --capture --now`) now also attempts Vision AI rating after capture

**Test it:**
1. Run `python3 calibrate.py --date 2026-02-25` (this day has 42 images)
2. Check `calibration_data/2026-02-25/manifest.json` -- `ai_score` should be a number, `ai_ratings` should have per-image entries
3. Run `python3 daily_sunset.py --capture --now` -- logs should show either "Rating N images via Vision AI..." or "No GEMINI_API_KEY -- skipping Vision AI rating" (both are acceptable)

---

## Phase 3: Light Cleanup

**Goal:** Remove dead code and fix docs that are out of sync with reality.

**Affected Files:**
- `.env` -- remove `OPENWEATHERMAP_API_KEY` line
- `sunset_predictor/config.py` -- remove `API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")` line
- `capture_sunset.py` -- replace the `--rate` stub (lines 244-247) with a real call to `rate_sunset_images()` from `sunset_predictor/rater.py`, or remove the `--rate` flag entirely if it's redundant with `calibrate.py`
- `README.md` -- fix: "3 scheduled jobs" -> "4 scheduled jobs", add the afternoon (14:00) job, add `--notify` flag, add `calibrate.py` to project layout, mention Telegram and Vision AI features
- `TESTING.md` -- fix: launchd test should list 4 jobs including `com.sunset.afternoon`, add Telegram notification test section, add Vision AI / calibrate test section

**Done means:** No dead references to OpenWeatherMap. README and TESTING.md accurately describe the current system. `capture_sunset.py --rate` either works or the flag is removed.

**Test it:**
1. Run `python3 -c "from sunset_predictor.config import *; print('OK')"` -- should not reference OPENWEATHERMAP
2. Run `python3 capture_sunset.py --help` -- should either show a working `--rate` flag or no `--rate` flag
3. Read `README.md` -- should mention 4 launchd jobs, Telegram, Vision AI, `calibrate.py`

---

## Phase 4: GitHub Repo + Future Vision

**Goal:** Package everything as a portfolio-ready GitHub project with a compelling README and a future vision doc.

**Affected Files:**
- `.gitignore` (new) -- exclude `.env`, `calibration_data/` (except `example/`), `__pycache__/`, `.DS_Store`, `*.log`, `.venv/`
- `README.md` -- full rewrite as portfolio piece: one-line hook, scoring model explanation (counter-intuitive insights), mermaid architecture diagram, calibration loop explanation, tech stack callout (all free APIs), Telegram screenshot placeholder, setup + run instructions
- `calibration_data/example/` (new directory) -- one sanitized sample day with `predictions.json`, `manifest.json`, and one sample image
- `docs/future_vision.md` (new) -- Instagram auto-posting, push notification app with revenue angle, multi-city expansion with API surface, community calibration flywheel. One page, concrete and credible.

**Done means:**
- `git status` shows a clean repo with all relevant files tracked
- README tells the full story in under 5 minutes of reading
- `docs/future_vision.md` exists and reads as a compelling product roadmap
- `.env` and `calibration_data/` (except example) are gitignored

**Test it:**
1. `git log --oneline` shows clean commit history
2. `git status` shows nothing untracked that should be tracked
3. Verify `.env` is NOT in the repo: `git ls-files .env` returns empty
4. Read `README.md` -- should have mermaid diagram, scoring explanation, setup guide
5. Read `docs/future_vision.md` -- should cover 4 expansion ideas

---

## Phase 5: Card Quality — Drivers Fix + Renderer Tests

**Goal:** Fix the P2-1 bug where low-score cards show contradictory positive drivers ("excellent visibility" on a score-2 card), and add test coverage for renderer helper functions.

**Affected Files:**
- `sunset_predictor/scorer.py` -- add `FACTOR_LABELS` and `FACTOR_LABELS_LOW` dicts (DRY: single source of truth for factor display names)
- `sunset_predictor/renderer.py` -- refactor `_top_drivers()` to use shared labels, invert sort for scores < 5.0
- `sunset_predictor/poster.py` -- refactor `_top_factors()` to use shared labels, same low-score logic
- `tests/test_renderer.py` (new) -- tests for `_lerp_color`, `_format_score`, `_tracking`, `_top_drivers`
- `tests/test_poster.py` -- add tests for `_top_factors` with high/low score predictions

**Done means:**
- A score-2 prediction card shows negative drivers like "blocked western sky" and "heavy low overcast" instead of "excellent visibility"
- A score-8 prediction card still shows positive drivers like "clear western horizon"
- Factor label dicts live in `scorer.py` only (no duplication in renderer.py / poster.py)
- `_lerp_color`, `_format_score`, `_tracking` all have test coverage
- All tests pass: `python3 -m pytest tests/ -v`

**Test it:**
1. Run `python3 -m pytest tests/ -v` -- all tests pass
2. Run `python3 render_card.py --score 2 --format feed` -- card should show negative driver phrasing
3. Run `python3 render_card.py --score 8 --format feed` -- card should show positive driver phrasing
4. Run `python3 main.py` -- exits 0
5. Run `python3 daily_sunset.py` -- exits 0

---

## Phase 6: OpenWeather Integration

**Goal:** Fix prediction accuracy by using OpenWeather as the primary weather source. Open-Meteo has consistently over-predicted (predicted 7.6 vs actual 5.5, predicted 6.4 vs actual 2.0). The competitor (sunset-predictor.com) which uses OpenWeather correctly predicted both bad sunsets.

**Affected Files:**
- `sunset_predictor/fetcher.py` -- add `OpenWeatherFetcher` class matching existing `OpenMeteoFetcher` interface
- `daily_sunset.py` -- use `OpenWeatherFetcher` when `OPENWEATHER_API_KEY` is set, fall back to `OpenMeteoFetcher`
- `.env.example` -- add `OPENWEATHER_API_KEY`
- `tests/test_fetcher.py` (new) -- response mapping, fallback, retry tests

**Done means:**
- With `OPENWEATHER_API_KEY` set, predictions use OpenWeather data
- Without the key, predictions use Open-Meteo (zero-config fallback)
- API response is correctly mapped to scorer input format
- Retry logic: 2 attempts with 15s timeout
- Weather source is logged in each prediction for debugging

**Test it:**
1. Run `python3 -m pytest tests/ -v` -- all tests pass
2. Run `python3 daily_sunset.py` -- logs should show which weather source was used
3. Compare a prediction with each source: set/unset `OPENWEATHER_API_KEY` and compare scores

---

## Phase 7: Complete Renderer Migration

**Goal:** Eliminate the Pillow rendering path. One rendering system (HTML/CSS renderer) for all visual output.

**Affected Files:**
- `post_sunset.py` -- use `renderer.render_feed_card` instead of `poster.generate_prediction_card`
- `sunset_predictor/renderer.py` -- add evening photo overlay function (replaces `poster.overlay_score`)
- `sunset_predictor/renderer.py` -- bundle local Inter `.woff2` fonts, remove Google Fonts CDN dependency
- `tests/test_poster.py` -- update card generation tests to use renderer

**Done means:**
- `post_sunset.py --prediction --dry-run` generates a card using the HTML/CSS renderer
- `post_sunset.py --photo --dry-run` generates an evening overlay using the renderer
- No Pillow font or gradient code is called anywhere in the live pipeline
- Cards render identically with or without internet (local fonts)

**Test it:**
1. Run `python3 post_sunset.py --prediction --dry-run` -- generates feed card in output/
2. Run `python3 post_sunset.py --photo --dry-run` -- generates evening photo with overlay
3. Disconnect from internet, render a card -- should work with local fonts
4. Run `python3 -m pytest tests/ -v` -- all tests pass
