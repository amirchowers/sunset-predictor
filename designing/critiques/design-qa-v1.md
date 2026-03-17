# Sunset Predictor — Design QA v1

**Role:** Design QA Lead
**Date:** 2026-03-17
**Reviewed:** `sample_feed.jpg` (7.6), `sample_story.jpg` (7.6), plus edge-case renders at scores 2, 3, 5.5, 10 — with/without tip, with long text
**Reference spec:** `Desiging/briefs/visual-system-v1.md`
**Reference tokens:** `Desiging/tokens/design-tokens.json`
**Renderer source:** `sunset-predictor/sunset_predictor/renderer.py`

---

## Overall verdict: CONDITIONAL PASS

The foundational direction is strong. The dark canvas, score-responsive accent, and left-aligned instrument aesthetic are all working. Typography hierarchy is clear at the hero level. But there are real production issues — two of which will break on actual content and one that fails mobile readability. These must be fixed before the first live post.

---

## What's working

- **Score as hero reads immediately.** 140px ExtraBold in accent color is the first thing the eye hits. Correct.
- **Score + "/10" baseline alignment works.** Flex baseline gap renders cleanly at all digit widths (single-digit "2", double-digit "10", fractional "7.6").
- **Score bar is proportionally correct.** Fill at 76% for 7.6, 20% for 2.0, 100% for 10.0 — all accurate.
- **Accent color progression is effective.** Steel blue (2) → muted warm (5.5) → amber (7.6) → orange (10). The system's signature feature works. You feel the score before you read it.
- **Tip container is clean.** Visible border, correct radius, "TODAY" label, proper padding. Wraps multi-line text correctly (verified on long-tip render).
- **Em-dash verdict formatting is correct.** "— Worth making plans for —" renders per spec.
- **Flat dark background.** No gradient, no texture. `#0D0D0F` is consistent across all renders.
- **No pure white or pure black used.** Color rules adhered to.
- **Feed and story are visually consistent.** Same system, scaled appropriately.

---

## Issues — Priority Order

---

### P0-1: Verdict line has no width constraint — WILL overflow

**Severity:** P0 — breaks on real content
**Observed in:** `feed_long_text.jpg` (score 5.5)
**What happens:** The verdict "Might catch something decent if you are already outside" renders as a single unbroken line. At 34px Medium, this text runs ~940px — right up to the edge of the 984px right boundary (96px margin). A verdict 2-3 characters longer will clip past the canvas.
**Why it matters:** The copy rule says "2-6 words," but the renderer has no visual guardrail. Real-world verdicts from the scorer module may exceed 6 words. One overflow post on Instagram and the brand looks broken.

**Fix — in `renderer.py`, `.verdict` CSS class:**

```css
.verdict {
  font-size: 34px;
  font-weight: 500;
  color: #C8BFA8;
  max-width: 888px;       /* ADD: constrain to content width */
  overflow-wrap: break-word; /* ADD: wrap long text */
  word-wrap: break-word;
}
```

**Also required — in `design-tokens.json`, add to verdict element:**

```json
{ "role": "verdict", "y_offset": 0, "format": "— {verdict} —", "max_width": "content_width" }
```

**Impact on downstream zones:** Once the verdict wraps, it pushes into the separator's absolute y-position (y:474). Fix P0-2 simultaneously.

---

### P0-2: Absolute y-positions break when any text wraps

**Severity:** P0 — architectural fragility
**What happens:** Every element in the info zone (verdict, separator, WHY, drivers) and the tip zone is absolutely positioned with hardcoded `top` values. If the verdict wraps to 2 lines (after P0-1 fix), the second line sits at ~y:462 while the separator is at y:474 — a 12px gap where the spec requires 24px (`space.md`). With a 3-line verdict: direct overlap.
**Root cause:** Absolute positioning cannot adapt to variable content height.

**Fix — convert the info zone and tip zone to flow layout:**

Replace the absolute-positioned verdict → separator → WHY → drivers → tip chain with a single absolutely-positioned container that uses normal CSS flow internally:

```html
<div class="el info-block" style="top:{verdict_y}px">
    <div class="verdict">— {verdict} —</div>
    <div class="sep"></div>
    <div class="lbl" style="margin-top:24px">WHY</div>
    <div class="drivers">{drivers}</div>
</div>
```

```css
.info-block {
  max-width: 888px;
}
.info-block .verdict {
  margin-bottom: 24px;
  overflow-wrap: break-word;
}
.info-block .sep {
  width: 60px; height: 1px;
  background: #2A2A30;
  margin-bottom: 24px;
}
.info-block .drivers {
  margin-top: 4px;
}
```

The info block's `top` is still absolute (anchored at y:424 feed / y:616 story), but everything inside it flows naturally. Same treatment for the tip zone — position the container absolutely, let content flow inside.

**Token update:** Remove individual `y_offset` values from info zone elements. The container handles stacking.

---

### P0-3: `text.tertiary` fails contrast for mobile readability

**Severity:** P0 — labels unreadable on phones in daylight
**What:** `text.tertiary` (`#6B6560`) on `bg.primary` (`#0D0D0F`) = **3.3:1 contrast ratio**. WCAG AA requires 4.5:1 for text this size (14px). The labels "TONIGHT'S SUNSET", "TEL AVIV", "WHY", "TODAY", and "SUNSET PREDICTOR" are all rendered in this color.
**On mobile:** 14px in a 1080px canvas displays at ~4.9pt apparent size on an iPhone (375pt width). Small text + low contrast + outdoor glare = invisible.
**The brand brief says "restrained."** Restrained is fine. Invisible is not. These labels carry structural information — they tell the viewer what zone they're reading. If the eye can't find "WHY", the drivers beneath it have no context.

**Fix — bump `text.tertiary` to `#8A8480`:**

| Before | After | Contrast |
|---|---|---|
| `#6B6560` (3.3:1) | `#8A8480` (4.9:1) | Passes AA |

This is a subtle lift — still clearly the lowest tier in the hierarchy, still warm-grey, still restrained. But now legible on a phone at noon.

**Update in `design-tokens.json`:**
```json
"tertiary": { "hex": "#8A8480", "rgb": [138, 132, 128] }
```

---

### P1-1: Story format without tip has a massive visual void

**Severity:** P1 — looks unfinished, not premium
**Observed in:** `story_score3_notip.jpg`
**What:** Content occupies the top ~25% of the story canvas (y:180 to ~y:470). The remaining ~1250px (65% of the canvas) is blank dark space with only the brand watermark at y:1700. On a phone, this looks like a rendering error, not a design choice.
**Why it matters:** The brand brief says "premium" and "sharp." A card that's 75% void reads as unfinished. It won't stop a thumb.

**Fix options (pick one):**

**Option A — Redistribute spacing vertically when there's no tip (recommended):**
For story format only, when `tip` is `None`, increase the spacers between header → score → info from 80/64/64px to approximately 140/100/100px. This pushes content toward the vertical center.

Implementation: in `_build_html()`, detect `tip is None and fmt == "story"`, then adjust zone y_starts accordingly. Add a `story_no_tip` layout variant to the tokens, or compute the adjustment inline.

**Option B — Vertically center the content block:**
Wrap all content in a flex container with `justify-content: center` and `min-height: 1520px` (content height minus safe areas). Content floats to vertical center regardless of how many zones render.

Option A is simpler and maintains the deliberate top-down reading order. Option B is more elegant but changes the reading rhythm.

---

### P1-2: Score bar fill is invisible at low scores

**Severity:** P1 — component fails at edge of its range
**Observed in:** `feed_score2_notip.jpg`
**What:** At score 2, the accent color is `#7D8A96` (cool grey-blue). The bar fill is 178px wide × 4px tall in this color against the `#16161A` track. The contrast ratio between the fill and the track is approximately 3.1:1 — borderline. On a phone, the bar reads as a thin grey line with no clear "fill vs track" distinction.
**Why it matters:** The score bar is data visualization. If the viewer can't distinguish fill from track, the bar adds visual clutter without communicating anything.

**Fix — add a subtle accent border to the track at low scores:**

In the CSS, always give the bar track a 1px border in the accent color at 25% opacity. This creates a faint outline that visually defines the component even when the fill is low-contrast:

```css
.bar-track {
  width: 888px; height: 4px;
  background: #16161A;
  border-radius: 2px;
  overflow: hidden;
  border: 1px solid rgba(R, G, B, 0.25); /* accent color at 25% */
}
```

Alternative: increase bar height to 6px for feed (8px for story). Thicker bar = easier to perceive contrast differences.

---

### P2-1: Drivers show contradictory data for low scores

**Severity:** P2 — copy/data issue, not a rendering bug
**Observed in:** `feed_score2_notip.jpg`
**What:** A score-2 "Skip it" card shows drivers "excellent visibility" and "clear western horizon." These are positive factors, but the overall score is bad. The card sends mixed signals.
**Root cause:** `_top_drivers()` always returns the top-scoring factors regardless of overall score. For a bad sunset, the drivers should explain WHY it's bad (e.g., "heavy overcast", "thick low clouds"), not what's going well.
**Note:** This is a data logic issue in `renderer.py::_top_drivers()` and the original `poster.py::_top_factors()`. Not a visual design bug, but it undermines the card's credibility.

**Fix:** For scores below 5, invert the sort — show the LOWEST-scoring factors (the ones dragging the score down) with appropriately negative phrasing. Define a parallel `_FACTOR_NAMES_LOW` map:

```python
_FACTOR_NAMES_LOW = {
    "cloud_high": "no high cloud color",
    "cloud_low_mid": "heavy low overcast",
    "western_near": "blocked western sky",
    ...
}
```

Or: let the `_top_drivers()` function detect score < 5 and reverse the sort + use negative phrasing.

---

### P2-2: Single-digit scores look asymmetric with "/10"

**Severity:** P2 — cosmetic
**Observed in:** `feed_score2_notip.jpg`, `feed_score10_tip.jpg`
**What:** The score "2" is a narrow glyph. The "/10" sits 8px to its right (flex gap). Visually, the "2 /10" combination has more whitespace between the number and the unit than "7.6 /10" does, because the "2" glyph is narrower. It's not wrong — baseline alignment is correct — but it looks slightly unbalanced.
**Fix (optional):** Use `font-variant-numeric: tabular-nums` on `.sc-num` to give all digits the same advance width. This makes "2" occupy the same horizontal space as "7" or "9", producing more consistent spacing. Inter supports tabular figures.

```css
.sc-num {
  font-variant-numeric: tabular-nums;
}
```

---

## Token/spec inconsistencies found

1. **Separator `space.md` spacing not enforced.** Spec says "Vertical margin: `space.md` above and below" for the separator, but the token zone definition uses `y_offset: 50` from the verdict — which is ~16px visual gap after the verdict's line-height, not 24px. The vertical spacing between verdict bottom and separator is tighter than spec.

2. **Tip label margin.** The CSS hardcodes `margin-bottom: 8px` between tip label and tip body. The token `y_offset` says 24px (feed) / 28px (story). The CSS should use the token value, not 8px.

3. **Story tip label size.** Token says `tip_label` in story uses 13px (same as feed). The spec table for story also says 13px. But the label should arguably scale to 15px for story to maintain relative hierarchy with the 24px tip body text.

---

## Exact fix sequence for the implementation agent

Run these in order. Each is independently testable.

### Fix 1: Add verdict width constraint + text wrapping
**File:** `renderer.py`, `.verdict` CSS
**Change:** Add `max-width:{cw}px; overflow-wrap:break-word;`
**Test:** Render with `--verdict "Might catch something decent if you are already outside"` — should wrap, not overflow

### Fix 2: Convert info zone from absolute to flow layout
**File:** `renderer.py`, `_build_html()` — info zone HTML + CSS
**Change:** Wrap verdict/separator/WHY/drivers in a single `div.info-block` positioned absolutely, with internal elements using flow layout (margin-based stacking)
**Test:** Render with 2-line verdict — separator and drivers should shift down naturally

### Fix 3: Bump `text.tertiary` to `#8A8480`
**File:** `design-tokens.json`, `color.text.tertiary`
**Change:** `"hex": "#8A8480", "rgb": [138, 132, 128]`
**Test:** All labels should be visibly lighter. Check that hierarchy still reads: primary > secondary > tertiary. No label should compete with the verdict or drivers.

### Fix 4: Fix tip label margin to use token value
**File:** `renderer.py`, `.tip-lbl` CSS
**Change:** Replace `margin-bottom:8px` with `margin-bottom:{tip_pad - 8}px` or read from token. For feed, this should be ~16px (to match the 24px y_offset minus the 8px label height). Simplest: set `margin-bottom:12px` for feed, `margin-bottom:16px` for story.
**Test:** Visual check that TODAY label has appropriate breathing room above tip body

### Fix 5: Add tabular-nums to score number
**File:** `renderer.py`, `.sc-num` CSS
**Change:** Add `font-variant-numeric:tabular-nums;`
**Test:** Render scores 2, 7.6, 10 side by side — digit spacing should look consistent

### Fix 6: Add story no-tip vertical redistribution
**File:** `renderer.py`, `_build_html()` — story zone positions
**Change:** When `tip is None and fmt == "story"`, increase spacers between header→score→info to fill more vertical space. Suggested adjusted y_starts: score.y_start = 440 (was 354), info.y_start = 740 (was 616).
**Test:** Story without tip should have content distributed across the top ~50% of canvas, not bunched in the top 25%.

### Fix 7: Score bar track border for low-score visibility
**File:** `renderer.py`, `.bar-track` CSS
**Change:** Add `outline: 1px solid {accent}33;` (accent at 20% opacity) or add a conditional `border` when score < 4.
**Test:** Render score 2 — bar track should be visually distinct from the background even when fill is minimal.

---

## Files to update

| File | Changes |
|---|---|
| `sunset-predictor/sunset_predictor/renderer.py` | Fixes 1, 2, 4, 5, 6, 7 (CSS + HTML structure) |
| `Desiging/tokens/design-tokens.json` | Fix 3 (tertiary color), Fix 4 (tip label margin token alignment) |
| `Desiging/briefs/visual-system-v1.md` | Update tertiary color in palette table; note flow layout for info zone |

---

## QA test matrix for post-fix verification

| Test case | Score | Tip | Verdict | Check |
|---|---|---|---|---|
| Happy path | 7.6 | yes | "Worth making plans for" | All zones render, no overflow |
| Long verdict | 5.5 | yes | "Might catch something decent if you are already outside" | Verdict wraps, separator/drivers shift down |
| No tip | 8.0 | no | "Tell your friends" | Tip zone absent, footer still bottom-anchored |
| Low score | 2.0 | no | "Skip it" | Cool accent, bar visible, labels readable |
| Max score | 10.0 | yes | "Once in a lifetime" | Hot orange accent, bar full, 2-digit score aligned |
| Minimal | 4.0 | no | "Meh" | Short verdict, no overflow, no visual gaps |
| Story no tip | 3.0 | no | "Overcast" | Content vertically distributed, not bunched at top |
| Story with tip | 7.6 | yes | "Worth making plans for" | Same as feed checks at story scale |
