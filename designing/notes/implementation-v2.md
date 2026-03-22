# Sunset Predictor — Implementation Notes v2

**Date:** 2026-03-17
**Author role:** Production Designer
**Status:** QA fixes applied. Renderer is production-ready for daily pipeline wiring.

---

## Changes since v1

This pass addressed all issues from `designing/critiques/design-qa-v1.md`. Seven fixes applied to `renderer.py`, one token update, one spec update.

---

## Fix summary

### P0-1: Verdict width constraint + text wrapping

**File:** `renderer.py` — `.verdict` CSS
**Change:** Added `overflow-wrap:break-word; word-wrap:break-word` and `margin-bottom:24px` (space.md). The `.info-block` container constrains width to `content_width`.
**Verified:** Long verdict "Might catch something decent if you are already outside" wraps to two lines without overflow.

### P0-2: Info zone converted from absolute to flow layout

**File:** `renderer.py` — `_build_html()` HTML + CSS
**Change:** Replaced individually-positioned verdict/separator/WHY/drivers/tip elements with a single `div.info-block` positioned absolutely at the info zone y_start. All children use margin-based flow layout internally. The tip box is also inside this flow container (no longer absolutely positioned), which prevents overlap when the verdict wraps to multiple lines.

**CSS structure:**
- `.info-block` — `width:{cw}px`, absolutely positioned at info zone origin
- `.verdict` — `margin-bottom:24px` (space.md), `overflow-wrap:break-word`
- `.sep` — `margin-bottom:24px` (space.md)
- `.drivers` — `margin-top:8px` (space.xs)
- `.tip-box` — `margin-top:40px` (space.lg for feed) or `56px` (space.xl for story), `width:100%`

**Verified:** Two-line verdict causes separator, drivers, and tip to shift down naturally.

### P0-3: Tertiary color contrast fix

**Files:** `design-tokens.json`, `visual-system-v1.md`
**Change:** `text.tertiary` bumped from `#6B6560` (3.3:1) to `#8A8480` (4.9:1 contrast ratio against `bg.primary`). Passes WCAG AA for the label sizes used.
**Verified:** Labels are visibly lighter but remain the lowest tier in the hierarchy. No label competes with verdict or drivers.

### P1-1: Story no-tip vertical redistribution

**File:** `renderer.py` — `_build_html()` zone positions
**Change:** When `tip is None and fmt == "story"`, score zone y_start shifts from 354→440 and info zone y_start shifts from 616→740. This increases the header→score spacer from ~80px to ~164px and score→info spacer from ~70px to ~108px.
**Verified:** Story without tip distributes content across the top ~45% of the canvas instead of bunching in the top 25%.

### P1-2: Score bar visibility at low scores

**File:** `renderer.py` — `.bar-track` CSS
**Change:** Added `box-shadow:0 0 0 1px {accent}33` (accent color at 20% opacity). Creates a subtle outline around the bar track that defines the component even when the fill is minimal.
**Verified:** Score 2 bar track is visually distinct from the background.

### P2-2: Tabular nums for consistent digit spacing

**File:** `renderer.py` — `.sc-num` CSS
**Change:** Added `font-variant-numeric:tabular-nums`. Inter supports tabular figures.
**Verified:** Scores 2, 7.6, 10 show consistent digit advance widths.

### Tip label margin fix

**File:** `renderer.py` — `.tip-lbl` CSS
**Change:** Replaced hardcoded `margin-bottom:8px` with `{sp_sm}px` (space.sm = 16px from spacing tokens). Provides adequate breathing room between the "TODAY" label and tip body text.
**Verified:** Visual improvement confirmed across feed and story formats.

---

## Architecture changes

### Flow layout for info + tip zones

The most significant structural change. The info zone (verdict → separator → WHY → drivers) and tip zone are now rendered inside a single absolutely-positioned container (`div.info-block`) that uses CSS flow layout internally.

**Before (v1):**
```
div.el.verdict    [position:absolute, top:424px]
div.el.sep        [position:absolute, top:474px]
div.el.lbl WHY    [position:absolute, top:498px]
div.el.drivers    [position:absolute, top:520px]
div.tip-box       [position:absolute, top:618px]
```

**After (v2):**
```
div.el.info-block [position:absolute, top:424px, width:888px]
  ├─ div.verdict    [flow, margin-bottom:24px]
  ├─ div.sep        [flow, margin-bottom:24px]
  ├─ div.lbl WHY    [flow]
  ├─ div.drivers    [flow, margin-top:8px]
  └─ div.tip-box    [flow, margin-top:40px, width:100%]
```

**Why this matters:** Variable-height content (wrapped verdicts, multi-line tips) now adapts naturally. No more overlap or fixed-gap assumptions.

---

## Files modified

| File | Changes |
|---|---|
| `sunset_predictor/renderer.py` | All 7 CSS/HTML fixes |
| `designing/tokens/design-tokens.json` | `text.tertiary` hex and RGB updated |
| `designing/briefs/visual-system-v1.md` | Palette table tertiary row updated |

---

## QA test matrix — all pass

| # | Test case | Score | Tip | Verdict | Result |
|---|---|---|---|---|---|
| 1 | Happy path | 7.6 | yes | "Worth making plans for" | PASS |
| 2 | Long verdict | 5.5 | yes | "Might catch something decent if you are already outside" | PASS |
| 3 | No tip | 8.0 | no | "Tell your friends" | PASS |
| 4 | Low score | 2.0 | no | "Skip it" | PASS |
| 5 | Max score | 10.0 | yes | "Once in a lifetime" | PASS |
| 6 | Minimal | 4.0 | no | "Meh" | PASS |
| 7 | Story no tip | 3.0 | no | "Overcast" | PASS |
| 8 | Story with tip | 7.6 | yes | "Worth making plans for" | PASS |

Test outputs saved to `output/qa/1-happy/` through `output/qa/8-story-tip/`.

Existing `test_poster.py` suite: **31/31 passed**.

---

## Known issue not addressed (data logic, not visual)

**P2-1: Contradictory drivers at low scores** — `_top_drivers()` still returns the highest-scoring factors regardless of overall score. A score-2 card showing "excellent visibility" and "clear western horizon" sends mixed signals. This requires a data logic fix (inverted sort + negative phrasing for low scores), not a visual fix. Tracked for a separate pass.

---

## Remaining work (unchanged from v1)

1. **Evening photo overlay badge** — still uses old Pillow renderer
2. **Pipeline wiring** — swap `poster.generate_prediction_card` → `renderer.render_feed_card`
3. **Local font files** — currently loads Inter from Google Fonts CDN
4. **Renderer-specific tests** — verify render dimensions, accent interpolation, format handling
