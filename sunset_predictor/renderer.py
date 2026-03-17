"""HTML/CSS card renderer for Sunset Predictor.

Renders prediction cards and story cards per the visual system spec.
All values are driven by Desiging/tokens/design-tokens.json.
Uses Playwright (headless Chromium) for pixel-perfect HTML-to-image rendering.

Public API:
    render_feed_card(prediction, tip=None) -> PIL.Image.Image
    render_story_card(prediction, tip=None) -> PIL.Image.Image
"""

import html as html_mod
import io
import json
import logging
from pathlib import Path
from typing import Optional

from PIL import Image

log = logging.getLogger("renderer")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TOKENS_PATH = _REPO_ROOT / "designing" / "tokens" / "design-tokens.json"

_tokens_cache: Optional[dict] = None


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------

def _load_tokens() -> dict:
    global _tokens_cache
    if _tokens_cache is None:
        with open(_TOKENS_PATH) as f:
            _tokens_cache = json.load(f)
    return _tokens_cache


# ---------------------------------------------------------------------------
# Color interpolation
# ---------------------------------------------------------------------------

def _lerp_color(score: float, anchors: list) -> str:
    """Interpolate accent color from score using RGB lerp between anchor points."""
    s = max(1.0, min(10.0, float(score)))
    lo, hi = anchors[0], anchors[-1]
    for i, a in enumerate(anchors):
        if a["score"] >= s:
            hi = a
            lo = anchors[max(0, i - 1)]
            break
    if lo["score"] == hi["score"]:
        return lo["hex"]
    t = (s - lo["score"]) / (hi["score"] - lo["score"])
    rgb = [int(lo["rgb"][j] + (hi["rgb"][j] - lo["rgb"][j]) * t) for j in range(3)]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def accent_color_for_score(score: float) -> str:
    """Public helper: get the accent hex color for a given score."""
    tokens = _load_tokens()
    return _lerp_color(score, tokens["color"]["accent"]["anchors"])


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

_FACTOR_NAMES = {
    "cloud_high": "high cirrus clouds",
    "cloud_low_mid": "clear low sky",
    "western_near": "clear western horizon",
    "western_far": "western cloud canvas",
    "humidity": "low humidity",
    "visibility": "excellent visibility",
    "air_quality": "good aerosol scattering",
    "weather_condition": "ideal weather",
}


def _top_drivers(prediction: dict, n: int = 2) -> list:
    """Extract top N scoring factors as readable noun phrases."""
    scores = prediction.get("scores", {})
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [_FACTOR_NAMES.get(k, k) for k, _ in ranked[:n]]


def _tracking(size: int, pct: float) -> str:
    """Convert tracking percentage to CSS letter-spacing value."""
    if pct == 0:
        return "normal"
    return f"{round(size * pct / 100, 2)}px"


def _format_score(score: float) -> str:
    """Format score for display — strip unnecessary trailing zeros."""
    if score == int(score):
        return str(int(score))
    return f"{score:.1f}"


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _build_html(
    prediction: dict,
    fmt: str,
    tokens: dict,
    tip: Optional[str] = None,
) -> str:
    """Build a complete self-contained HTML document for a card."""
    layout = tokens["layout"][fmt]
    scale = tokens["typography"]["scale"][fmt]
    c = tokens["color"]
    comp = tokens["components"]

    w, h = layout["canvas_w"], layout["canvas_h"]
    ml = layout["margin_left"]
    cw = layout["content_width"]

    score = prediction["score"]
    score_display = _format_score(score)
    verdict = html_mod.escape(prediction["verdict"])
    sunset_time = prediction.get("sunset_local", "")
    city = html_mod.escape(prediction.get("city", "TEL AVIV"))
    accent = _lerp_color(score, c["accent"]["anchors"])
    drivers = _top_drivers(prediction)

    # Score bar geometry
    bar = comp["score_bar"][fmt]
    fill_w = max(score / 10.0 * cw, comp["score_bar"]["min_fill_px"])

    # --- Compute y-positions from zone definitions ---
    z = layout["zones"]

    hy = z["header"]["y_start"]
    label1_y = hy + z["header"]["elements"][0]["y_offset"]
    time_y   = hy + z["header"]["elements"][1]["y_offset"]
    city_y   = hy + z["header"]["elements"][2]["y_offset"]

    sy = z["score"]["y_start"]
    score_y = sy + z["score"]["elements"][0]["y_offset"]
    bar_y   = sy + z["score"]["elements"][1]["y_offset"]

    iy = z["info"]["y_start"]
    verdict_y = iy + z["info"]["elements"][0]["y_offset"]
    sep_y     = iy + z["info"]["elements"][1]["y_offset"]
    why_y     = iy + z["info"]["elements"][2]["y_offset"]
    drivers_y = iy + z["info"]["elements"][3]["y_offset"]
    driver_lh = z["info"]["elements"][3]["line_height"]

    tz = z["tip"]
    tip_y   = tz["y_start"]
    tip_pad = tz["container"]["padding"]
    tip_br  = tz["container"]["border_radius"]

    footer_y = z["footer"]["y_value"]

    s = scale

    # --- Conditional elements ---
    time_el = ""
    if sunset_time:
        time_el = (
            f'<div class="el time" style="top:{time_y}px">'
            f"{sunset_time}</div>"
        )

    drivers_el = ""
    if drivers:
        divs = "".join(f"<div>{html_mod.escape(d)}</div>" for d in drivers)
        drivers_el = (
            f'<div class="el lbl" style="top:{why_y}px">WHY</div>\n'
            f'    <div class="el drivers" style="top:{drivers_y}px">{divs}</div>'
        )

    tip_el = ""
    if tip:
        tip_safe = html_mod.escape(tip)
        tip_el = (
            f'<div class="tip-box" style="top:{tip_y}px">\n'
            f'        <div class="tip-lbl">TODAY</div>\n'
            f'        <div class="tip-txt">{tip_safe}</div>\n'
            f"    </div>"
        )

    # --- Assemble ---
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=block" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{
  width:{w}px;height:{h}px;
  background:{c["bg"]["primary"]["hex"]};
  font-family:'Inter',sans-serif;
  overflow:hidden;
  -webkit-font-smoothing:antialiased;
}}
.card{{position:relative;width:{w}px;height:{h}px}}
.el{{position:absolute;left:{ml}px}}

.lbl{{
  font-size:{s["label"]["size"]}px;
  font-weight:{s["label"]["weight"]};
  text-transform:uppercase;
  letter-spacing:{_tracking(s["label"]["size"], s["label"]["tracking_pct"])};
  color:{c["text"]["tertiary"]["hex"]};
}}
.time{{
  font-size:{s["sunset_time"]["size"]}px;
  font-weight:{s["sunset_time"]["weight"]};
  letter-spacing:{_tracking(s["sunset_time"]["size"], s["sunset_time"]["tracking_pct"])};
  color:{c["text"]["primary"]["hex"]};
}}
.sc-line{{display:flex;align-items:baseline;gap:8px}}
.sc-num{{
  font-size:{s["score_number"]["size"]}px;
  font-weight:{s["score_number"]["weight"]};
  letter-spacing:{_tracking(s["score_number"]["size"], s["score_number"]["tracking_pct"])};
  color:{accent};line-height:1;
}}
.sc-unit{{
  font-size:{s["score_unit"]["size"]}px;
  font-weight:{s["score_unit"]["weight"]};
  color:{c["text"]["tertiary"]["hex"]};line-height:1;
}}
.bar-track{{
  width:{cw}px;height:{bar["height"]}px;
  background:{c["bg"]["surface"]["hex"]};
  border-radius:{bar["radius"]}px;overflow:hidden;
}}
.bar-fill{{
  height:100%;width:{fill_w:.0f}px;
  background:{accent};
  border-radius:{bar["radius"]}px;
}}
.verdict{{
  font-size:{s["verdict"]["size"]}px;
  font-weight:{s["verdict"]["weight"]};
  color:{c["text"]["secondary"]["hex"]};
}}
.sep{{width:60px;height:1px;background:{c["separator"]["hex"]}}}
.drivers div{{
  font-size:{s["drivers"]["size"]}px;
  font-weight:{s["drivers"]["weight"]};
  color:{c["text"]["secondary"]["hex"]};
  line-height:{driver_lh}px;
}}
.tip-box{{
  position:absolute;left:{ml}px;width:{cw}px;
  background:{c["bg"]["surface"]["hex"]};
  border:1px solid {c["bg"]["surface_border"]["hex"]};
  border-radius:{tip_br}px;padding:{tip_pad}px;
}}
.tip-lbl{{
  font-size:{s["tip_label"]["size"]}px;
  font-weight:{s["tip_label"]["weight"]};
  text-transform:uppercase;
  letter-spacing:{_tracking(s["tip_label"]["size"], s["tip_label"]["tracking_pct"])};
  color:{c["text"]["tertiary"]["hex"]};margin-bottom:8px;
}}
.tip-txt{{
  font-size:{s["tip_body"]["size"]}px;
  font-weight:{s["tip_body"]["weight"]};
  color:{c["text"]["primary"]["hex"]};line-height:1.5;
}}
.brand{{
  font-size:{s["brand_mark"]["size"]}px;
  font-weight:{s["brand_mark"]["weight"]};
  text-transform:uppercase;
  letter-spacing:{_tracking(s["brand_mark"]["size"], s["brand_mark"]["tracking_pct"])};
  color:{c["text"]["tertiary"]["hex"]};
}}
</style></head><body>
<div class="card">
    <div class="el lbl" style="top:{label1_y}px">TONIGHT\u2019S SUNSET</div>
    {time_el}
    <div class="el lbl" style="top:{city_y}px">{city}</div>

    <div class="el sc-line" style="top:{score_y}px">
        <span class="sc-num">{score_display}</span><span class="sc-unit">/10</span>
    </div>
    <div class="el" style="top:{bar_y}px">
        <div class="bar-track"><div class="bar-fill"></div></div>
    </div>

    <div class="el verdict" style="top:{verdict_y}px">\u2014 {verdict} \u2014</div>
    <div class="el sep" style="top:{sep_y}px"></div>
    {drivers_el}

    {tip_el}

    <div class="el brand" style="top:{footer_y}px">SUNSET PREDICTOR</div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Playwright screenshot
# ---------------------------------------------------------------------------

def _screenshot(html: str, width: int, height: int) -> Image.Image:
    """Render HTML to a PIL Image using Playwright headless Chromium."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is required for rendering. Install with:\n"
            "  pip install playwright && python -m playwright install chromium"
        )

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
        )
        page.set_content(html, wait_until="networkidle")
        page.evaluate("() => document.fonts.ready")
        png_bytes = page.screenshot(type="png")
        browser.close()

    return Image.open(io.BytesIO(png_bytes)).convert("RGB")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_feed_card(prediction: dict, tip: Optional[str] = None) -> Image.Image:
    """Render a 1080x1080 feed prediction card. Returns PIL Image (RGB)."""
    tokens = _load_tokens()
    html = _build_html(prediction, "feed", tokens, tip)
    log.info("Rendering feed card — score %s", prediction["score"])
    return _screenshot(html, 1080, 1080)


def render_story_card(prediction: dict, tip: Optional[str] = None) -> Image.Image:
    """Render a 1080x1920 story prediction card. Returns PIL Image (RGB)."""
    tokens = _load_tokens()
    html = _build_html(prediction, "story", tokens, tip)
    log.info("Rendering story card — score %s", prediction["score"])
    return _screenshot(html, 1080, 1920)
