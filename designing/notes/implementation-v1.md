# Sunset Predictor — Implementation Notes v1

**Date:** 2026-03-17
**Author role:** Production Designer
**Status:** Feed and story rendering working. Evening overlay not yet migrated.

---

## Rendering approach

### Decision: HTML/CSS + Playwright (headless Chromium)

**Why not Pillow (the old approach):**
Pillow has no native letter-spacing, no font-weight selection (requires separate .ttf files per weight), no text wrapping, no border-radius containers, and no baseline alignment. Implementing the visual system spec in Pillow would mean reimplementing half of CSS by hand — fragile, slow to iterate, and impossible to preview in a browser.

**Why not SVG:**
SVG has no auto text wrapping, awkward letter-spacing support, and requires manual path construction for rounded-rect containers with borders. Font embedding is complex. For a text-heavy card, SVG is the wrong tool.

**Why HTML/CSS:**
Every property in the design spec maps to a native CSS property: `letter-spacing`, `font-weight`, `border-radius`, `line-height`, `text-transform`. The card template is plain HTML/CSS that can be opened in any browser for inspection. Layout changes are CSS edits, not pixel math. Playwright renders it to a pixel-perfect screenshot in ~2 seconds.

**The tradeoff:**
Playwright adds ~150MB (Chromium binary) and renders at ~2s/card vs ~100ms with Pillow. But we render 2 cards/day, not 2000. Typography fidelity and maintainability matter infinitely more than render speed here.

---

## Architecture

```
sunset-predictor/
  sunset_predictor/
    renderer.py        ← NEW: HTML/CSS rendering engine
    poster.py          ← UNCHANGED: captions, tips, Instagram posting, old Pillow renderer
  render_card.py       ← NEW: CLI for generating sample/test cards
  output/
    sample_feed.jpg    ← generated sample (1080x1080)
    sample_story.jpg   ← generated sample (1080x1920)
  requirements.txt     ← UPDATED: added playwright

  designing/
    tokens/
      design-tokens.json ← source of truth for all visual values
    briefs/
      visual-system-v1.md ← design system specification
    critiques/
      direction-review-v1.md ← creative direction review
      design-qa-v1.md ← QA report with prioritized fixes
```

### Data flow

```
prediction dict (JSON)
  ↓
renderer._build_html()     reads design-tokens.json
  ↓                        computes accent color from score
  ↓                        builds HTML string with CSS
  ↓
renderer._screenshot()     launches Playwright Chromium
  ↓                        loads HTML, waits for fonts
  ↓                        takes PNG screenshot
  ↓
PIL.Image (RGB)            1080x1080 or 1080x1920
  ↓
.save("card.jpg")          JPEG quality 95
```

---

## What was built

### `sunset_predictor/renderer.py`

Public API:

| Function | Returns | Description |
|---|---|---|
| `render_feed_card(prediction, tip=None)` | `PIL.Image.Image` (1080x1080, RGB) | Feed prediction card |
| `render_story_card(prediction, tip=None)` | `PIL.Image.Image` (1080x1920, RGB) | Story prediction card |
| `accent_color_for_score(score)` | `str` (hex) | Score-to-accent color lookup |

Internals:
- `_load_tokens()` — loads and caches `design-tokens.json`
- `_lerp_color()` — RGB interpolation between 10 accent anchors
- `_build_html()` — assembles complete HTML document from tokens + prediction data
- `_screenshot()` — Playwright headless render → PIL Image
- `_top_drivers()` — extracts top scoring factors as readable phrases
- `_tracking()` — converts tracking percentage to CSS `letter-spacing`

### `render_card.py`

CLI for generating cards without the full pipeline:

```bash
python3 render_card.py                                    # both formats, sample data
python3 render_card.py --feed --score 9.2 --verdict "Tell your friends"
python3 render_card.py --story --no-tip
python3 render_card.py --json path/to/prediction.json     # real data
```

---

## What was NOT built (remaining work)

### 1. Evening photo overlay badge

The old `overlay_score()` in `poster.py` still uses Pillow with a black rectangle badge. It needs to be rewritten to match the design system's evening badge spec:
- `bg.primary` at 88% opacity
- 1px accent-colored border at 35% opacity
- 8px border radius
- Inter font (Bold 40px for score, Medium 15px for verdict)

This is a straightforward Pillow update (badge dimensions are small enough that Pillow works fine) or could use a mini HTML render.

### 2. Wiring into the daily pipeline

`poster.py` still exports `generate_prediction_card()` which uses the old Pillow gradient renderer. To switch the pipeline to the new renderer:

```python
# In poster.py or post_sunset.py, replace:
from sunset_predictor.poster import generate_prediction_card

# With:
from sunset_predictor.renderer import render_feed_card as generate_prediction_card
```

The API is compatible — both take `(prediction, tip=None)` and return `PIL.Image.Image`.

### 3. Local font files

The renderer currently loads Inter from Google Fonts CDN at render time. For full offline determinism, download Inter `.ttf` files to `assets/fonts/` and reference them via `@font-face` with `file://` paths or base64 data URIs. Low priority — Google Fonts is extremely reliable and the pipeline already needs internet for weather API + Instagram.

### 4. Test updates

The existing `test_poster.py` tests the old `generate_prediction_card()`. New tests should:
- Verify `render_feed_card()` returns 1080x1080 RGB
- Verify `render_story_card()` returns 1080x1920 RGB
- Verify rendering with and without tip
- Verify `_lerp_color()` at boundary scores (1.0, 5.5, 10.0)
- Verify `_format_score()` for whole and fractional scores

---

## Token-driven design

Every visual value comes from `designing/tokens/design-tokens.json`:
- Colors (background, text tiers, accent anchors)
- Typography (sizes, weights, tracking percentages per role)
- Layout (canvas dimensions, margins, zone y-positions, element offsets)
- Component specs (score bar, tip container, separator)

To change any visual property, edit the JSON — no code changes needed. The renderer reads tokens at runtime.

---

## Dependencies added

| Package | Version | Purpose |
|---|---|---|
| `playwright` | 1.58.0 | Headless Chromium for HTML-to-image rendering |

Chromium browser binary is installed separately via `python -m playwright install chromium` (~91MB).

---

## QA checklist for the next agent

### Visual checks (compare against `designing/briefs/visual-system-v1.md`)

- [ ] Background is flat `#0D0D0F`, no gradient
- [ ] Score number is in accent color (warm amber for 7.6)
- [ ] "/10" is in `text.tertiary`, lighter weight, baseline-aligned with score
- [ ] Score bar track spans full content width, fill is proportional to score
- [ ] Verdict has em-dashes: "— text —"
- [ ] WHY label is uppercase with wide tracking
- [ ] Drivers are readable noun phrases
- [ ] Tip container has `bg.surface` background with visible border and border-radius
- [ ] "TODAY" label is uppercase, tertiary color
- [ ] "SUNSET PREDICTOR" watermark is at bottom-left, uppercase, wide tracking
- [ ] All text is left-aligned to the left margin
- [ ] Card is 1080x1080 (feed) or 1080x1920 (story)

### Accent color checks

Run these to verify the score-responsive palette:
```bash
python3 render_card.py --feed --score 2 --verdict "Skip it" --no-tip --output-dir output/test
python3 render_card.py --feed --score 5 --verdict "Might be decent" --no-tip --output-dir output/test
python3 render_card.py --feed --score 7.6 --verdict "Worth making plans for" --output-dir output/test
python3 render_card.py --feed --score 9.5 --verdict "Tell your friends" --output-dir output/test
```

- Score 2: cool blue-grey accent
- Score 5: muted warm accent
- Score 7.6: warm amber accent
- Score 9.5: bright gold accent

### Layout checks

- [ ] No text overflow at any score/verdict length
- [ ] Card without tip: tip zone absent, no empty container visible
- [ ] Card without drivers: WHY section absent
- [ ] Long verdict (6 words) fits without clipping
- [ ] Long tip (2 sentences) wraps properly inside container

### Technical checks

- [ ] `render_feed_card()` returns PIL Image with mode "RGB" and size (1080, 1080)
- [ ] `render_story_card()` returns PIL Image with mode "RGB" and size (1080, 1920)
- [ ] Renderer fails gracefully with clear error if Playwright not installed
- [ ] Existing `poster.py` tests still pass (no breaking changes)

### Sample outputs

Generated outputs for QA review:
- `sunset-predictor/output/sample_feed.jpg`
- `sunset-predictor/output/sample_story.jpg`
