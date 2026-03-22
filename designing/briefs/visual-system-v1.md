# Sunset Predictor — Visual System v1

**Direction:** "The Instrument" (Direction A from `Desiging/critiques/direction-review-v1.md`)
**Date:** 2026-03-17
**Status:** Ready for implementation
**Tokens file:** `Desiging/tokens/design-tokens.json`

---

## Design Concept

Sunset Predictor as a precision instrument. A beautiful gauge reading on a dark canvas, where the score *glows* warmer as the sunset gets better. Calm, authoritative, premium. Every card is data you can feel before you read it.

---

## 1. Color Palette

### Base colors

| Token | Hex | RGB | Role |
|---|---|---|---|
| `bg.primary` | `#0D0D0F` | 13, 13, 15 | Card background (near-black) |
| `bg.surface` | `#16161A` | 22, 22, 26 | Elevated containers (tip box, badge) |
| `bg.surface-border` | `#2A2A30` | 42, 42, 48 | Container borders, separators |
| `text.primary` | `#F0EDE8` | 240, 237, 232 | Main text (warm white, not pure) |
| `text.secondary` | `#C8BFA8` | 200, 191, 168 | Verdict, time, supporting text |
| `text.tertiary` | `#8A8480` | 138, 132, 128 | Labels, footer, metadata |
| `separator` | `#2A2A30` | 42, 42, 48 | Thin rules between zones |

### Score-responsive accent palette

The accent color shifts with the score. This is the system's signature feature — followers learn to *feel* the score from the color before reading the number.

| Score | Token | Hex | RGB | Semantic |
|---|---|---|---|---|
| 1.0 | `accent.1` | `#6B7B8D` | 107, 123, 141 | Steel — skip it |
| 2.0 | `accent.2` | `#7D8A96` | 125, 138, 150 | Cool grey |
| 3.0 | `accent.3` | `#8B9DAF` | 139, 157, 175 | Muted blue-grey |
| 4.0 | `accent.4` | `#A8946E` | 168, 148, 110 | Warming up |
| 5.0 | `accent.5` | `#C4956A` | 196, 149, 106 | Muted warm |
| 6.0 | `accent.6` | `#D99B52` | 217, 155, 82 | Amber emerging |
| 7.0 | `accent.7` | `#E8A84C` | 232, 168, 76 | Warm amber |
| 8.0 | `accent.8` | `#F0B83A` | 240, 184, 58 | Rich gold |
| 9.0 | `accent.9` | `#F5C542` | 245, 197, 66 | Bright gold |
| 10.0 | `accent.10` | `#FF8C42` | 255, 140, 66 | Hot amber — legendary |

**Interpolation rule:** For fractional scores (e.g., 7.6), linearly interpolate RGB between the two nearest anchor colors. Implementation: `lerp(accent.7, accent.8, 0.6)`.

### Color usage rules

- Background is ALWAYS `bg.primary`. No gradients. No textures. Flat.
- Score number is ALWAYS rendered in the interpolated accent color.
- Score bar fill uses the same accent color.
- Only ONE accent color per card — derived from the score.
- Text never uses pure white (`#FFFFFF`) or pure black (`#000000`).

---

## 2. Typography

### Font

**Inter** — free, open-source, designed for screens, excellent weight range, has tabular/monospaced number variants.

- Download: https://github.com/rsms/inter/releases
- Required files: `Inter-Light.ttf`, `Inter-Regular.ttf`, `Inter-Medium.ttf`, `Inter-SemiBold.ttf`, `Inter-Bold.ttf`, `Inter-ExtraBold.ttf`
- Store at: `sunset-predictor/assets/fonts/`

### Type scale (feed card — 1080x1080)

| Role | Size (px) | Weight | Case | Letter-spacing | Color token |
|---|---|---|---|---|---|
| Score number | 140 | ExtraBold (800) | As-is | -3% | `accent.[score]` |
| Score unit ("/10") | 48 | Light (300) | As-is | 0 | `text.tertiary` |
| Verdict | 34 | Medium (500) | Sentence case | 0 | `text.secondary` |
| Sunset time | 32 | SemiBold (600) | As-is | +1% | `text.primary` |
| Label | 14 | Medium (500) | UPPERCASE | +10% | `text.tertiary` |
| Drivers | 21 | Regular (400) | Sentence case | 0 | `text.secondary` |
| Tip body | 21 | Regular (400) | Sentence case | 0 | `text.primary` |
| Tip label | 13 | Medium (500) | UPPERCASE | +10% | `text.tertiary` |
| Brand mark | 14 | Medium (500) | UPPERCASE | +14% | `text.tertiary` |

### Type scale (story — 1080x1920)

| Role | Size (px) | Weight |
|---|---|---|
| Score number | 180 | ExtraBold (800) |
| Score unit | 56 | Light (300) |
| Verdict | 40 | Medium (500) |
| Sunset time | 38 | SemiBold (600) |
| Label | 16 | Medium (500) |
| Drivers | 24 | Regular (400) |
| Tip body | 24 | Regular (400) |
| Brand mark | 14 | Medium (500) |

### Typography rules

- Score number and "/10" sit on the SAME baseline but are different sizes, weights, and colors. The score is the hero; "/10" is a quiet unit label.
- Verdict is always wrapped in em-dashes: `— Verdict text —`
- Labels are ALWAYS uppercase with wide tracking. They precede their data on a separate line.
- No italics anywhere. The system is purely weight-driven.
- No text shadow, no stroke, no glow effects.

---

## 3. Spacing Scale

Base unit: **8px**

| Token | Value | Use |
|---|---|---|
| `space.xs` | 8px | Minimum gap, inline spacing |
| `space.sm` | 16px | Between label and its value |
| `space.md` | 24px | Between related content blocks |
| `space.lg` | 40px | Between major zones |
| `space.xl` | 56px | Hero breathing room (above/below score) |
| `space.2xl` | 80px | Top margin |
| `space.3xl` | 96px | Left/right margin |

---

## 4. Layout — Feed Post (1080x1080)

### Grid

```
Canvas: 1080 x 1080

Margins:
  left:   96px
  right:  96px
  top:    80px
  bottom: 56px

Content width: 888px (1080 - 96 - 96)
Content height: 944px (1080 - 80 - 56)

Alignment: LEFT (all content left-aligned to left margin)
```

### Zone map

All y-positions are from top of canvas. All x-positions start at 96px (left margin).

```
┌─────────────────────────────────────────┐
│                                         │
│  80px margin-top                        │
│                                         │
│  ── HEADER ZONE ──────────────────────  │
│  [LABEL] "TONIGHT'S SUNSET"   14px     │  y: 80
│  [TIME]  "17:49"              32px     │  y: 110
│  [CITY]  "TEL AVIV"          14px     │  y: 154
│                                         │
│  ── 56px spacer ──────────────────────  │
│                                         │
│  ── SCORE ZONE ───────────────────────  │
│  [SCORE] "7.6"  /10          140+48px  │  y: 228
│  [BAR]   ████████████░░░░     4px h    │  y: 380
│                                         │
│  ── 40px spacer ──────────────────────  │
│                                         │
│  ── INFO ZONE ────────────────────────  │
│  [VERDICT] "— Worth making plans —"    │  y: 424
│  ── separator line (60px wide) ──────  │  y: 474
│  [LABEL] "WHY"               14px     │  y: 498
│  [DRIVERS] "High cirrus clouds"       │  y: 520
│  [DRIVERS] "Clear western horizon"    │  y: 550
│                                         │
│  ── 40px spacer ──────────────────────  │
│                                         │
│  ── TIP ZONE (optional) ─────────────  │
│  ┌ bg.surface container, 24px padding ┐│  y: 618
│  │ [TIP LABEL] "TODAY"        13px    ││
│  │ [TIP BODY]  "Grab a falafel..."   ││
│  └────────────────────────────────────┘│
│                                         │
│  ── flexible space ──────────────────  │
│                                         │
│  ── FOOTER ZONE ──────────────────────  │
│  [BRAND] "SUNSET PREDICTOR"   14px     │  y: 1024 (bottom-anchored)
│                                         │
│  56px margin-bottom                     │
└─────────────────────────────────────────┘
```

### Zone rules

- **Header zone:** Label "TONIGHT'S SUNSET" in uppercase tertiary, followed by time in `text.primary` SemiBold, then city label in uppercase tertiary. Tight vertical stacking (`space.sm`).
- **Score zone:** Score number left-aligned, accent color, ExtraBold. "/10" follows on same baseline, in `text.tertiary`, Light weight. Below: score bar.
- **Score bar:** 4px tall. Full content width (888px) as track in `bg.surface`. Filled portion = `(score / 10) * 888px` in accent color. Rounded ends (2px radius).
- **Info zone:** Verdict text in `text.secondary`, preceded and followed by em-dash. Below verdict: a 60px-wide separator line in `separator` color, 1px thick, left-aligned. Then "WHY" label and drivers list.
- **Tip zone:** Only rendered when tip text exists. Container: `bg.surface` background, 1px `bg.surface-border` border, 12px border-radius, 24px padding. Contains "TODAY" label and tip body.
- **Footer zone:** Brand wordmark "SUNSET PREDICTOR" in uppercase, widest tracking, `text.tertiary`. Anchored to bottom margin.

### Handling missing data

| Missing element | Behavior |
|---|---|
| No tip | Tip zone does not render. Space collapses. Footer stays anchored to bottom. |
| No sunset time | Time line omitted, city moves up. |
| No drivers | "WHY" section omitted, separator still appears below verdict. |
| Score only (minimal) | Render score zone and verdict only. Everything else optional. |

---

## 5. Layout — Story (1080x1920)

### Grid

```
Canvas: 1080 x 1920

Margins:
  left:   80px
  right:  80px
  top:    180px  (safe area for Instagram status bar / close button)
  bottom: 220px  (safe area for reply bar / swipe zone)

Content width: 920px
Content height: 1520px

Alignment: LEFT
```

### Zone map

```
┌─────────────────────────────────────────┐
│  180px safe area (top)                  │
│                                         │
│  ── HEADER ZONE ──────────────────────  │
│  [LABEL] "TONIGHT'S SUNSET"           │  y: 180
│  [TIME]  "17:49"                       │  y: 212
│  [CITY]  "TEL AVIV"                   │  y: 260
│                                         │
│  ── 80px spacer ──────────────────────  │
│                                         │
│  ── SCORE ZONE ───────────────────────  │
│  [SCORE] "7.6"  /10          180+56px  │  y: 354
│  [BAR]   ████████████░░░░     6px h    │  y: 546
│                                         │
│  ── 64px spacer ──────────────────────  │
│                                         │
│  ── INFO ZONE ────────────────────────  │
│  [VERDICT]                             │  y: 616
│  ── separator ───────                  │  y: 676
│  [LABEL] "WHY"                         │  y: 706
│  [DRIVERS]                             │  y: 732
│                                         │
│  ── 64px spacer ──────────────────────  │
│                                         │
│  ── TIP ZONE ─────────────────────────  │
│  (same container style, scaled up)     │
│                                         │
│  ── flexible space ──────────────────  │
│                                         │
│  ── FOOTER ZONE ──────────────────────  │
│  [BRAND]                               │  y: 1700 (bottom-anchored)
│                                         │
│  220px safe area (bottom)               │
└─────────────────────────────────────────┘
```

### Story-specific rules

- Score number is 180px (larger than feed) to dominate vertical real estate.
- Score bar is 6px tall (thicker than feed for visibility on small phones).
- All vertical spacers grow proportionally (roughly 1.5x feed spacers).
- Same colors, same fonts, same alignment, same accent logic.

---

## 6. Evening Photo Overlay (Score Badge)

Overlaid on sunset webcam photo posts.

### Badge spec

| Property | Value |
|---|---|
| Width | 260px |
| Height | 110px |
| Background | `bg.primary` at 88% opacity |
| Border | 1px, accent color at 35% opacity |
| Border radius | 8px |
| Position | Bottom-right, 32px margin from canvas edge |

### Badge internal layout

```
┌──────────────────────────────┐
│  16px padding                │
│  [SCORE] "7.6/10"   Bold 40px, accent color
│  [VERDICT] short     Medium 15px, text.secondary
│  16px padding                │
└──────────────────────────────┘
```

- Score and verdict are center-aligned within the badge.
- Score uses accent color matched to the card system.
- Verdict is truncated to fit (max ~20 characters).

---

## 7. Copy Rules

Derived from brand brief voice: *short, confident, not cute, not overexcited, not poetic for the sake of it.*

### Verdict

- 2–6 words.
- Em-dash separators on the card: `— Verdict text —`
- Tone: declarative, calm. As if a sommelier is describing a wine.
- Good: "Worth making plans for" / "Average — clouds won't help" / "Rare golden hour setup"
- Bad: "OMG amazing sunset incoming!!!" / "A beautiful evening awaits you"

### Drivers

- Noun phrases, not sentences.
- Each starts lowercase unless proper noun.
- Good: "high cirrus clouds" / "clear western horizon" / "excellent visibility"
- Bad: "There are high clouds in the sky" / "The visibility is really good"

### Tip

- 1–2 sentences maximum.
- Specific and grounded. Mention a real place, drink, food, or activity.
- Never mentions the score.
- Good: "Grab a cold Goldstar and find a bench on the Tayelet."
- Bad: "Enjoy the beautiful sunset with someone special!"

### Action line

- Only appears when score >= 7.
- Imperative form. Short.
- Good: "Head to the port." / "Find a rooftop."
- Bad: "You should consider going outside to enjoy this!"

### Banned words (never use on card or caption)

`amazing`, `stunning`, `beautiful`, `gorgeous`, `breathtaking`, `incredible`, `spectacular`, `magnificent`, `awesome`, `unbelievable`, `perfect`

### Emoji rules

- Zero emojis on card visuals. Ever.
- Caption may use 1–2 minimal emojis maximum (sun, pin, thermometer). No faces, no hands, no strings of emojis.

---

## 8. Component Behaviors

### Score bar

- **Track:** Full content width, `bg.surface` fill, 4px height (6px story), 2px border-radius.
- **Fill:** `(score / 10.0) * content_width` pixels wide, accent color, same border-radius.
- **Minimum fill:** Even a 0/10 renders 4px of fill so the bar is never invisible.
- **Animation (if ever used in motion):** Fill grows left-to-right over 600ms, ease-out.

### Tip container

- Only renders when tip text is non-null and non-empty.
- Background: `bg.surface`
- Border: 1px solid `bg.surface-border`
- Border radius: 12px
- Padding: 24px all sides
- Contains: "TODAY" label (13px, uppercase, tertiary) + tip body text (21px, primary)
- Max height: unlimited (text wraps within container, container grows)
- Text wraps at container width minus padding.

### Separator line

- Width: 60px, fixed.
- Height: 1px.
- Color: `separator` token.
- Left-aligned to content margin.
- Vertical margin: `space.md` above and below.

### Brand watermark

- Text: "SUNSET PREDICTOR"
- All uppercase, 14px, Medium weight, +14% letter-spacing.
- Color: `text.tertiary`.
- Position: left-aligned, anchored to bottom of content area.
- Never changes. Not dynamic.

---

## 9. Responsive Behavior

There are only two sizes. No responsive breakpoints — each is a fixed canvas.

| Format | Canvas | Use |
|---|---|---|
| Feed post | 1080 x 1080 | Instagram feed square |
| Story | 1080 x 1920 | Instagram story / Reels cover |

If future formats are needed (Twitter card, web embed), derive from the feed post by adjusting margins and type scale proportionally.

---

## 10. File Structure for Implementation

```
sunset-predictor/
  assets/
    fonts/
      Inter-Light.ttf
      Inter-Regular.ttf
      Inter-Medium.ttf
      Inter-SemiBold.ttf
      Inter-Bold.ttf
      Inter-ExtraBold.ttf
  sunset_predictor/
    poster.py          ← rewrite rendering logic here
    design_tokens.py   ← (optional) Python import of tokens from JSON
  Desiging/
    tokens/
      design-tokens.json  ← source of truth for all values
```

---

## 11. Implementation Checklist

For the agent implementing this system:

1. Download Inter font family `.ttf` files → `assets/fonts/`
2. Create accent color interpolation function (10 anchor points, RGB lerp)
3. Rewrite `generate_prediction_card()` using this spec
4. Rewrite `overlay_score()` badge using this spec
5. Add story card generation function
6. Remove all gradient code (`_draw_gradient`, `GRADIENT_TOP/MID/BOTTOM`)
7. Wire font loading to bundled `.ttf` files instead of system font search
8. Test with scores: 2.0, 5.0, 7.6, 9.5, 10.0 — verify accent color progression
9. Test with and without tip text — verify layout collapses correctly
10. Test with long verdict and long tip text — verify word wrapping
11. Run QA checklist: contrast, alignment, legibility at 375px display width (iPhone)
