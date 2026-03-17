# AGENTS.md

Operational instructions for any AI agent working in `sunset-predictor`.

## Working Directory

Always run commands from:

`/Users/amir.chowers/Desktop/AI Project /sunset-predictor`

**WARNING:** The workspace folder name has a **trailing space** (`AI Project ` not `AI Project`). Shell commands must quote the path.

## Getting Started

**Read these files in order:**
1. `README.md` -- current status, what works, how to run
2. This `AGENTS.md` -- map, purpose, how to work here
3. `docs/spec.md` -- full project spec (source of truth for requirements)
4. `docs/plan.md` -- phased implementation plan with task checklists
5. `TESTING.md` -- manual QA procedures

**Then verify the foundation:**

```bash
python3 main.py
python3 daily_sunset.py
```

Both should exit 0.

## Project Map

### Entry Points (root)
- `main.py` -- single prediction to console
- `daily_sunset.py` -- daily pipeline: predict, capture, notify, post (main automation entrypoint)
- `post_sunset.py` -- Instagram posting (`--prediction` for noon card, `--photo` for sunset frame)
- `capture_sunset.py` -- legacy predict + capture (standalone, predates daily_sunset.py)
- `calibrate.py` -- batch Vision AI rating (`--date YYYY-MM-DD`, rates images and writes AI score to manifest)
- `backtest.py` -- historical scoring to CSV
- `rate_day.py` -- human rating CLI
- `retro_review.py` -- 7-day calibration report
- `discover_cameras.py` -- find YouTube live webcams
- `render_card.py` -- CLI tool for generating sample prediction cards (feed/story). Usage: `python3 render_card.py --score 7.6 --format both`

### Package: `sunset_predictor/`
- `config.py` -- `Location` dataclass, `DEFAULT_LOCATION` (Tel Aviv)
- `sun.py` -- sunset time, azimuth, western sky geometry
- `fetcher.py` -- Open-Meteo weather + air quality API
- `scorer.py` -- 8-factor weighted scoring engine, verdicts
- `formatter.py` -- CLI output formatting
- `cameras.py` -- webcam registry (6 YouTube live thumbnail sources)
- `rater.py` -- Vision AI sunset rating (Gemini primary, HuggingFace GLM-4.5V fallback)
- `notifier.py` -- Telegram notification (sends daily prediction message)
- `poster.py` -- Instagram auto-posting (prediction cards, score overlays, captions, Gemini tips)
- `renderer.py` -- **NEW** HTML/CSS card renderer (Playwright + headless Chromium). Replaces Pillow-based rendering in `poster.py`. Token-driven: reads all visual values from `designing/tokens/design-tokens.json`.

### Design System: `designing/`
- `briefs/brand-brief.md` -- brand identity, audience, voice, positioning
- `briefs/visual-system-v1.md` -- full design system spec: colors, typography, spacing, layout, components, copy rules
- `tokens/design-tokens.json` -- machine-readable design tokens (renderer reads this at runtime)
- `critiques/direction-review-v1.md` -- creative direction review + 3 visual directions, recommended "The Instrument"
- `critiques/design-qa-v1.md` -- QA report against visual system spec (P0/P1/P2 issues with exact fixes)
- `notes/implementation-v1.md` -- renderer implementation notes, architecture, remaining work
- `prompts/` -- prompt templates used to drive each design phase

### Data
- `calibration_data/YYYY-MM-DD/` -- per-day: `predictions.json`, `manifest.json`, `*.jpg`, `daily.log`
- `calibration_data/retro_7d.csv` and `retro_7d.md` -- weekly reports

### Automation
- `launchd/` -- 4 macOS plists + install/uninstall scripts
- Schedule: 08:00, 12:00 (+ `--notify --post`), 14:00, 16:00 (`--capture --post`)

### Docs (`docs/`)
- `docs/spec.md` -- full project spec (source of truth)
- `docs/plan.md` -- phased implementation plan with checkboxes
- `docs/product_doc.md` -- product context and background
- `TESTING.md` -- manual QA checklist (at root for visibility)

## Project Purpose

A sunset quality predictor for Tel Aviv that scores sunsets 1-10 using weather data, captures webcam frames for calibration, and sends daily alerts via Telegram. Dual purpose: a real daily-use product and a portfolio piece for interviews.

Keep it practical, shippable, and simple. Prefer interpretable scoring over premature complexity. Preserve calibration data quality.

## Critical Rules

- Never commit secrets (`.env` stays local, `.gitignore` must exclude it)
- Never silently swallow errors in data pipelines
- If behavior differs from docs, update docs in the same session
- If introducing a flag/feature, implement it fully or hide it
- Python 3.9 on this Mac -- avoid `X | Y` union type syntax, use `Optional[X]` from `typing`
- No paid APIs -- Open-Meteo, YouTube thumbnails, and Telegram are all free

## Technical Gotchas

**Webcam thumbnails:** Use `sddefault_live.jpg`, not `maxresdefault_live.jpg`. Small YouTube streams don't generate high-res thumbnails. Already configured correctly in `cameras.py`.

**Thumbnail refresh rate:** Updates roughly every 5 minutes, not real-time. Acceptable for the 30-min sunset capture window.

**Camera fleet:** 5 Ashdod beach cams + 1 Israel multi-cam grid. Ashdod is ~30km south of Tel Aviv, same coastline and sunset conditions. No reliable Tel Aviv-specific live cams exist.

**launchd + Desktop permissions:** `/usr/bin/python3` needs Full Disk Access (System Settings > Privacy > Full Disk Access) to read scripts on Desktop. Already granted.

**Gemini model version matters:** `gemini-2.0-flash` has zero quota (deprecated). Use `gemini-2.5-flash` (5 RPM, 20 RPD free tier). The rater uses `gemini-2.5-flash` as primary.

**HuggingFace free credits reset periodically:** Rating many images can temporarily exhaust credits (402 error), but they come back. The auto-router URL is `https://router.huggingface.co/v1/chat/completions`. GLM-4.5V needs `max_tokens: 500+` or its thinking mode may produce empty content.

**Camera fleet reduced to ashdod_arches only:** Conserves Vision AI credits. `get_cameras()` filters to this one camera. All 6 cameras remain in the `CAMERAS` list for future re-expansion.

**Scoring model is v1:** All weights are hand-tuned. First calibration: predicted 6.8 vs human-rated 6.0. Western sky factor overscores when scattered low/mid clouds exist without cirrus.

**Instagram (instagrapi):** Uses unofficial Instagram API. One post/day from a dedicated account is safe. Store credentials in `.env` (never commit). If Instagram challenges the login (e.g., from a new IP), you may need to verify via the app. The `--dry-run` flag generates images and captions without posting — use for testing. **Python 3.9 fix required:** instagrapi 2.x uses `str | None` syntax (Python 3.10+). Two files need manual patching after install: `instagrapi/types.py` (line 451: `ClipsMetadata | dict` → `Union[ClipsMetadata, dict]`) and `instagrapi/__init__.py` (3 occurrences of `X | None` → `Optional[X]`, plus add `from typing import Optional`). If you reinstall instagrapi, you must re-apply these patches.

**Dead ends documented (don't retry):**
- OpenWeatherMap: slow key activation, worse cloud data than Open-Meteo
- Windy.com webcams: paid API only
- SkylineWebcams: protected streams
- BeachCam.co.il: no public API
- ffmpeg + yt-dlp: YouTube CDN blocks non-browser clients
- `maxresdefault_live.jpg` for small streams: returns channel avatar

## Daily Pipeline

`daily_sunset.py` is the main automation entrypoint:
- Runs prediction, appends to `calibration_data/YYYY-MM-DD/predictions.json`
- Can be called multiple times per day; each call stacks a new entry
- `--capture`: grabs webcam frames around sunset
- `--capture --now`: captures immediately
- `--notify`: sends prediction to Telegram

**launchd** triggers it 4 times daily:
- 08:00 morning prediction
- 12:00 noon prediction + Telegram notification
- 14:00 afternoon prediction
- 16:00 capture job (waits dynamically for sunset)

Only the 16:00 job requires the Mac to be awake. Install via `bash launchd/install.sh`.

## Iron Laws

These are absolute. Not guidelines. Not suggestions.

1. **NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.** Write code before the test? Delete it. Start over. Don't keep it as "reference." Don't "adapt" it. Delete means delete.
2. **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.** If you haven't traced the data flow and formed a hypothesis, you cannot propose fixes.
3. **NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.** Run the command. Read the output. Then claim the result. "Should work" is not evidence.

## TDD Workflow

**Red-Green-Refactor for every change:**

1. **RED:** Write one minimal failing test showing what should happen. Run it. Confirm it fails.
2. **GREEN:** Write the simplest code to pass the test. Run it. Confirm it passes and no other tests break.
3. **REFACTOR:** Clean up. Keep tests green.

**Test infrastructure:** `pytest` in `tests/` directory. Run with `python3 -m pytest tests/ -v`.

**What to test:**
- `sunset_predictor/scorer.py` — threshold functions and weighted scoring (retrofit existing code)
- `sunset_predictor/rater.py` — response parsing, fallback logic (TDD for new code)
- `sunset_predictor/notifier.py` — message formatting (TDD for new code)
- `calibrate.py` — manifest reading/writing (TDD for new code)
- Don't mock external APIs unless unavoidable — test the logic around them

**Red flags — all mean delete code, start over:**
- Code before test
- Test passes immediately on first run
- "I already manually tested it"
- "Too simple to test"
- Modifying tests to make them pass

## Systematic Debugging

When something breaks, follow this order. Complete each phase before proceeding.

1. **Root cause investigation:** Read error messages carefully. Reproduce consistently. Check recent changes (`git diff`). Trace data flow to find where bad values originate.
2. **Pattern analysis:** Find working examples in the codebase. Compare against the broken code. List every difference.
3. **Hypothesis testing:** Form a single hypothesis ("X is the root cause because Y"). Test with the smallest possible change. One variable at a time.
4. **Implementation:** Write a failing test that reproduces the bug. Fix the root cause. Verify fix. If 3+ fixes fail, STOP — question the architecture and discuss with me.

## Feedback Loops and Log Observability

This project runs as launchd automation — you can't watch it live. Design for agent self-sufficiency:

- **launchd logs:** `calibration_data/launchd_morning.log`, `launchd_noon.log`, `launchd_afternoon.log`, `launchd_capture.log` — read these to diagnose pipeline issues
- **Per-day logs:** `calibration_data/YYYY-MM-DD/daily.log` — one-line-per-run append log
- **All logging uses `logging` module** with timestamps (`%(asctime)s [%(levelname)s] %(message)s`). Keep this consistent in new code.
- **Fail loud:** If an API call fails, log the error with context (URL, status code, response body). Never silently return empty data.
- **Close feedback loops without screenshots:** Every feature should be verifiable via terminal commands, log files, or JSON output. Minimize situations that require manual browser/phone testing.

## Engineering Principles

**YAGNI:** Don't build features until they're needed. Every line of code is a liability. Build the simplest thing that works, add complexity only when reality demands it. If something is in the "Parking Lot" section of `docs/spec.md`, don't build it.

**DRY:** Every piece of knowledge must have a single representation. When you see duplication, extract it. When you're about to copy-paste, stop and abstract. This project already has some duplication between `capture_sunset.py` and `daily_sunset.py` -- don't add more.

**Simple over easy:** Choose designs that keep concerns independent. Favor composition over interleaving. Separate data from behavior, configuration from code. Judge an approach by the long-term properties of the system it produces, not by how easy it is to start.

**Minimize dependencies:** Default to stdlib and existing packages first. This project uses `requests`, `astral`, `python-dotenv`, and `google-generativeai`. Before adding a new package, explain why and what alternatives you considered. Prefer `requests` to call APIs directly over adding wrapper libraries (e.g., the Telegram notifier uses raw `requests` instead of `python-telegram-bot`).

**Concrete examples in this project:**
- `notifier.py` uses `requests` directly instead of adding `python-telegram-bot` -- fewer deps, same result
- `rater.py` HuggingFace fallback should use `requests` to the Inference API, not add `huggingface-hub`
- Scoring factors are simple threshold functions, not ML models -- interpretable and debuggable
- Each module (`scorer`, `fetcher`, `cameras`, `notifier`, `rater`) is independent and swappable

## Collaboration Style

- Explain your approach before writing code
- Explain at a low level -- define technical terms before using them
- Code comments explain "why" not "what"
- Pause to check in, don't barrel ahead
- When requirements are unclear, state your assumption explicitly and proceed

## Phase Wrap-Up Protocol

Before considering any phase or task complete, follow this protocol:

1. **Run verification and show output:**
   - `python3 main.py` exits 0
   - `python3 daily_sunset.py` exits 0
   - Any phase-specific tests from TESTING.md -- show actual output
   - Never say "tests should pass" -- show the evidence

2. **Verify phase objectives:**
   - Read `docs/plan.md` objectives line by line
   - Check each off with evidence
   - State what remains if anything is incomplete

3. **Update documentation:**
   - `README.md` -- current status
   - `TESTING.md` -- QA steps for new features
   - `docs/spec.md` / `docs/plan.md` -- if implementation differed from plan, update with rationale

4. **Walk me through testing:**
   - Concrete steps: "Run X, you should see Y"
   - Not "test the feature"

5. **Wait for my confirmation before proceeding to next phase.**

6. **Memory sweep:** Ask "What did I learn that future sessions need to know?" Update AGENTS.md if anything.

7. **Offer to commit** with a clear message referencing the phase.

CRITICAL: Never say "Phase complete, moving on" without my explicit sign-off.

## Version Control

- Propose commit messages and wait for confirmation
- Format: `type: description` with bullet points
- Branch strategy: `feature/description` or `fix/description` -- never commit directly to main
- Never commit: `.env`, `calibration_data/` (except `example/`), `__pycache__/`, `.DS_Store`
- Always commit: `requirements.txt`, `.env.example` (not `.env`)

## Continuous Documentation

As you work, update docs immediately -- don't wait for wrap-up:
- **AGENTS.md**: gotchas discovered, patterns that work, things that would confuse a future agent
- **docs/spec.md**: when implementation differs from plan
- **README.md**: when status or capabilities change
- **TESTING.md**: when new features need QA steps

Ask yourself: "What would confuse a future agent about this?"

## Common Commands

```bash
python3 -m pytest tests/ -v                  # run all tests
python3 main.py                              # prediction to console
python3 daily_sunset.py                      # log a prediction
python3 daily_sunset.py --notify             # log prediction + send to Telegram
python3 daily_sunset.py --notify --post      # log prediction + Telegram + Instagram card
python3 daily_sunset.py --capture --post     # log prediction + capture + Instagram photo
python3 daily_sunset.py --capture --now      # log prediction + capture immediately
python3 daily_sunset.py --capture            # log prediction + capture at sunset window
python3 post_sunset.py --prediction --dry-run  # generate prediction card (no post)
python3 post_sunset.py --prediction          # post prediction card to Instagram
python3 post_sunset.py --photo --dry-run     # generate sunset photo overlay (no post)
python3 post_sunset.py --photo               # post sunset photo to Instagram
python3 capture_sunset.py                    # legacy: predict + snapshot
python3 rate_day.py --date YYYY-MM-DD --score N  # set human rating
python3 retro_review.py --days 7             # 7-day calibration report
python3 calibrate.py --date YYYY-MM-DD        # batch Vision AI rating
python3 backtest.py                          # historical scoring
bash launchd/install.sh                      # install daily automation
bash launchd/uninstall.sh                    # remove daily automation
```

## Last Session Handoff (2026-03-17, session 7)

**What changed (session 7 — Design System & Renderer):**
- Full design system built: brand brief → creative direction critique → visual system spec → design tokens → HTML/CSS renderer → design QA
- `designing/` folder added to repo with all design artifacts (briefs, tokens, critiques, notes, prompts)
- `sunset_predictor/renderer.py` — new HTML/CSS rendering engine using Playwright + headless Chromium, fully driven by `design-tokens.json`
- `render_card.py` — CLI tool for generating sample cards
- `requirements.txt` updated with `playwright` dependency
- Renderer tokens path corrected: now reads from `designing/tokens/design-tokens.json` inside the repo (was previously reading from `../Desiging/` outside the repo)
- `.gitignore` updated to exclude `output/` (generated sample images)
- QA report written to `designing/critiques/design-qa-v1.md` with P0/P1/P2 issues and exact fixes

**What changed (session 6 — Instagram Go-Live):**
- Instagram account created: `@sunsetpredictor`
  - Bio: "Tonight's sunset: meh or magic? We'll tell you by noon. Follow for daily Tel Aviv sunset forecasts."
  - Registered with work email (amir.chowers@unity3d.com) — user plans to swap to personal email before leaving the company
  - 2FA is OFF (required for instagrapi API login)
  - Account warmed up: profile pic set, follows added, bio written
- First live Instagram post succeeded (2026-03-16): prediction card with 7.6/10 score and hardcoded lifestyle tip
- Second live post succeeded (2026-03-17): full automated pipeline — Telegram + Instagram + Gemini tip ("Grab a felafel and perch yourself on the ancient walls")
- `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` added to `.env`
- instagrapi 2.3.0 installed with Python 3.9 compatibility patches (see gotchas below)
- **launchd jobs reinstalled** — the previously loaded jobs were stale (had `--notify --post` in the plist file but the loaded jobs were from an older version without those flags). Ran `bash launchd/uninstall.sh && bash launchd/install.sh` to fix. This was the root cause of missing Telegram notifications for several days.
- Human rating logged: 2026-03-16 predicted 7.6, user rated 5.5. Overscoring pattern: clouds blocked sun at horizon instead of catching light. Model can't distinguish cloud position relative to sun.
- Pushed to GitHub (2 commits: session 5 handoff + session 6 handoff)

**Previous sessions (Phases 0–5):**
- Phase 0 verified: `main.py`, `daily_sunset.py`, and `notifier.py` import all exit 0
- Phase 0.5 complete: test infrastructure, 156 scorer/notifier tests
- Phase 1 complete: Telegram notification, `@Sunsettlvbot`, `--notify` flag, all 4 launchd jobs
- Phase 2 complete: Vision AI calibration loop (Gemini + HuggingFace fallback), `calibrate.py`, 195 tests
- Phase 3 complete: dead code removed, docs synced with reality
- Phase 4 complete: GitHub repo live at https://github.com/amirchowers/sunset-predictor
- Session 5: Instagram auto-posting feature built, committed, pushed. 228 tests passing.
- Session 6: Instagram account created, first live post successful

**What is next:**
- Everything is live and automated: Telegram + Instagram + Gemini tips fire daily at noon via launchd
- **Design system v1 built (session 7):** Brand brief → creative direction → visual system → design tokens → HTML/CSS renderer → QA. See `designing/critiques/design-qa-v1.md` for the QA report with prioritized fixes.
- **Immediate next step:** Implement QA fixes from `design-qa-v1.md` (P0: text wrapping, flow layout, contrast; P1: story no-tip layout, low-score bar visibility; P2: tabular-nums, negative driver display)
- **Then:** Wire `renderer.py` into the daily pipeline (replace Pillow calls in `poster.py`), rewrite evening photo overlay badge, add local fonts for offline determinism, write tests for `_lerp_color()` and `_format_score()`
- Future: swap Instagram email from work to personal before user leaves company
- Future: improve scoring model — western sky/cloud factor overscores when clouds block the sun vs catch its light (see 2026-03-16 calibration: predicted 7.6, actual 5.5)

**GitHub push credentials:**
- User has a fine-grained PAT (Contents: Read and write) — can be regenerated at https://github.com/settings/personal-access-tokens/new
- Push method: temporarily set remote URL with token, push, then reset URL to clean version
- `git remote set-url origin https://amirchowers:<TOKEN>@github.com/amirchowers/sunset-predictor.git && git push && git remote set-url origin https://github.com/amirchowers/sunset-predictor.git`

**Known issues/gotchas (cumulative):**
- **Design tokens are the source of truth for rendering.** All visual values (colors, typography, spacing, layout) live in `designing/tokens/design-tokens.json`. The renderer reads this at runtime — change the JSON, change the output. Don't hardcode visual values in `renderer.py`.
- **Playwright + Chromium required for rendering.** `pip3 install playwright && python3 -m playwright install chromium`. Adds ~400MB. Renders take ~1-2s per card (vs instant with Pillow). Acceptable for 2 cards/day.
- **Renderer uses Google Fonts CDN for Inter.** Requires internet at render time. Future: bundle local `.woff2` files for offline determinism.
- **Score accent color interpolation:** RGB linear lerp between 10 anchor points in the tokens file. `renderer._lerp_color()` handles fractional scores. Test edge cases: score 1.0, 10.0, and values between anchors.
- **QA report has open P0 issues:** See `designing/critiques/design-qa-v1.md`. These must be fixed before wiring the renderer into the live pipeline.
- `gemini-2.0-flash` has zero quota (deprecated). `gemini-2.5-flash` works (5 RPM, 20 RPD free). Already updated in `rater.py`.
- Gemini 2.5 uses thinking tokens — needs `max_output_tokens: 1024` (not 256) or the content may be truncated.
- Gemini lifestyle tip quota: 20 RPD free tier. If exhausted from testing, tips silently skip until next day. The noon Telegram/Instagram post still works, just without the tip line.
- HuggingFace credits are not permanent — they reset periodically. 402 errors are temporary.
- GLM-4.5V uses a thinking mode: it has `reasoning_content` (thinking trace) and `content` (answer). When content is empty, we fall back to `reasoning_content`.
- GLM-4.5V sometimes wraps JSON in text — the `_parse_rating_response` regex fallback handles this.
- The HF auto-router URL is `https://router.huggingface.co/v1/chat/completions` (NOT `router.huggingface.co/hf-inference/models/...` which returns 404 for VLM models).
- AI rates daytime captures as score 1 — correct behavior but drags down the average in batch runs.
- Camera fleet reduced to `ashdod_arches` only to conserve credits (4 imgs/day vs 24).
- `google.generativeai` library is deprecated — Google recommends switching to `google.genai`. Works for now but should migrate in a future phase.
- Python 3.9 on this Mac — use `Optional[X]` not `X | None`.
- `_score_western_near` uses strict `>` comparisons (not `>=`) — boundary values at exact thresholds fall to the next bucket. Tests document this precisely.
- **instagrapi 2.3.0 + Python 3.9:** requires manual patching after install. Two files: (1) `instagrapi/types.py` line 451: change `Optional[ClipsMetadata | dict]` → `Optional[Union[ClipsMetadata, dict]]`, (2) `instagrapi/__init__.py`: add `from typing import Optional`, change 3 occurrences of `str | None` and `list | None` to `Optional[str]` / `Optional[list]`. If instagrapi is ever reinstalled or upgraded, these patches must be re-applied.
- **instagrapi 1.x is dead:** Instagram returns `unsupported_version` for the API version used by instagrapi <2.0. Don't downgrade.
- **Instagram first login challenge:** New accounts + first API login triggers a challenge. User must approve "Was this you?" from the Instagram app before API login succeeds. After the first successful login, subsequent logins are smooth.

**Troubleshooting: missing Telegram notifications:**
- launchd only fires when the Mac is awake and running. If the user reports not receiving a noon Telegram notification, the most likely cause is the Mac was asleep or lid-closed at 12:00.
- macOS will catch up on the most recent missed `StartCalendarInterval` job when the Mac wakes — but only the latest missed one, not all.
- If the Mac was powered off at the scheduled time, the job is missed entirely with no catch-up.
- The 16:00 capture job is most at risk since it may fall after the user closes the laptop for the day.

**Troubleshooting: Instagram posting failures:**
- Check `.env` has `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` set
- Test login: `python3 -c "from dotenv import load_dotenv; load_dotenv(); from instagrapi import Client; import os; cl = Client(); cl.login(os.getenv('INSTAGRAM_USERNAME'), os.getenv('INSTAGRAM_PASSWORD')); print('OK')"`
- If challenge error: open Instagram app, approve login, retry
- If `unsupported operand type(s) for |`: instagrapi patches were lost (reinstall or upgrade wiped them). Re-apply the Python 3.9 patches documented above.
- If `unsupported_version`: you're on instagrapi <2.0. Upgrade to 2.x and patch.
