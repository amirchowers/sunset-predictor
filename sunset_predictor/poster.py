"""Instagram posting module — prediction cards, score overlays, and auto-posting.

Generates two types of Instagram content:
1. Noon prediction card: designed graphic with score, verdict, and lifestyle tip
2. Evening sunset photo: best webcam frame with score overlay badge

Uses Pillow for image generation, Gemini for tip generation, instagrapi for posting.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from sunset_predictor.scorer import FACTOR_LABELS, FACTOR_LABELS_LOW

log = logging.getLogger("poster")

CARD_SIZE = (1080, 1080)

# Sunset gradient colors
GRADIENT_TOP = (45, 10, 60)       # deep purple
GRADIENT_MID = (180, 60, 30)      # burnt orange
GRADIENT_BOTTOM = (255, 160, 50)  # warm gold


# ---------------------------------------------------------------------------
# Image Generation
# ---------------------------------------------------------------------------

def _draw_gradient(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a three-stop vertical sunset gradient."""
    mid_y = height // 2
    for y in range(height):
        if y < mid_y:
            ratio = y / mid_y
            r = int(GRADIENT_TOP[0] + (GRADIENT_MID[0] - GRADIENT_TOP[0]) * ratio)
            g = int(GRADIENT_TOP[1] + (GRADIENT_MID[1] - GRADIENT_TOP[1]) * ratio)
            b = int(GRADIENT_TOP[2] + (GRADIENT_MID[2] - GRADIENT_TOP[2]) * ratio)
        else:
            ratio = (y - mid_y) / (height - mid_y)
            r = int(GRADIENT_MID[0] + (GRADIENT_BOTTOM[0] - GRADIENT_MID[0]) * ratio)
            g = int(GRADIENT_MID[1] + (GRADIENT_BOTTOM[1] - GRADIENT_MID[1]) * ratio)
            b = int(GRADIENT_MID[2] + (GRADIENT_BOTTOM[2] - GRADIENT_MID[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a clean font, falling back to default if system fonts aren't available."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/System/Library/Fonts/SFCompact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> list:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def generate_prediction_card(prediction: dict, tip: Optional[str] = None) -> Image.Image:
    """Generate a 1080x1080 prediction card with score, verdict, and optional tip."""
    img = Image.new("RGB", CARD_SIZE)
    draw = ImageDraw.Draw(img)
    _draw_gradient(draw, CARD_SIZE[0], CARD_SIZE[1])

    font_title = _get_font(52)
    font_score = _get_font(120)
    font_verdict = _get_font(42)
    font_tip = _get_font(34)
    font_footer = _get_font(28)

    white = (255, 255, 255)
    white_soft = (255, 255, 255, 200)

    score = prediction["score"]
    verdict = prediction["verdict"]
    sunset_time = prediction.get("sunset_local", "")

    draw.text((CARD_SIZE[0] // 2, 160), "Tonight\u2019s Sunset", font=font_title,
              fill=white, anchor="mm")

    if sunset_time:
        draw.text((CARD_SIZE[0] // 2, 220), sunset_time, font=font_verdict,
                  fill=(255, 220, 180), anchor="mm")

    draw.text((CARD_SIZE[0] // 2, 400), f"{score} / 10", font=font_score,
              fill=white, anchor="mm")

    draw.text((CARD_SIZE[0] // 2, 500), f"\u201c{verdict}\u201d", font=font_verdict,
              fill=(255, 220, 180), anchor="mm")

    if tip:
        lines = _wrap_text(tip, font_tip, CARD_SIZE[0] - 160, draw)
        y = 650
        for line in lines:
            draw.text((CARD_SIZE[0] // 2, y), line, font=font_tip, fill=white, anchor="mm")
            y += 45

    draw.text((CARD_SIZE[0] // 2, CARD_SIZE[1] - 60), "Sunset Predictor \u2022 Tel Aviv",
              font=font_footer, fill=(200, 180, 160), anchor="mm")

    return img


def overlay_score(image_path: Path, score: float, verdict: str) -> Image.Image:
    """Overlay a score badge on a sunset webcam frame."""
    img = Image.open(image_path).convert("RGB")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = img.size
    badge_w, badge_h = int(w * 0.35), int(h * 0.18)
    margin = int(w * 0.03)
    x0 = w - badge_w - margin
    y0 = h - badge_h - margin

    draw.rounded_rectangle(
        [(x0, y0), (x0 + badge_w, y0 + badge_h)],
        radius=12,
        fill=(0, 0, 0, 160),
    )

    font_score = _get_font(max(28, int(badge_h * 0.45)))
    font_verdict = _get_font(max(14, int(badge_h * 0.22)))

    cx = x0 + badge_w // 2
    draw.text((cx, y0 + badge_h * 0.35), f"{score}/10",
              font=font_score, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((cx, y0 + badge_h * 0.72), verdict,
              font=font_verdict, fill=(255, 220, 180, 255), anchor="mm")

    composite = Image.alpha_composite(img.convert("RGBA"), overlay)
    return composite.convert("RGB")


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------

def _top_factors(prediction: dict, n: int = 2) -> list:
    """Return the top N scoring factors by score value.

    For scores >= 5.0: highest-scoring factors with positive phrasing.
    For scores < 5.0: lowest-scoring factors with negative phrasing.
    """
    scores = prediction.get("scores", {})
    overall = prediction.get("score", 10.0)
    if overall < 5.0:
        sorted_factors = sorted(scores.items(), key=lambda x: x[1])
        labels = FACTOR_LABELS_LOW
    else:
        sorted_factors = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        labels = FACTOR_LABELS
    return [labels.get(k, k) for k, _ in sorted_factors[:n]]


def build_noon_caption(prediction: dict, tip: Optional[str] = None) -> str:
    """Build the Instagram caption for the noon prediction post."""
    score = prediction["score"]
    verdict = prediction["verdict"]
    sunset_time = prediction.get("sunset_local", "")
    condition = prediction.get("raw", {}).get("condition", "")

    top = _top_factors(prediction)
    why = " + ".join(top) if top else condition

    lines = [
        f"Tonight\u2019s sunset: {score}/10 \u2014 \u201c{verdict}\u201d",
        "",
        f"Why: {why.capitalize()}.",
    ]

    if sunset_time:
        lines.append(f"Sunset at {sunset_time}.")

    comfort = prediction.get("comfort", {})
    temp = comfort.get("temp_c")
    if temp is not None:
        lines.append(f"Temperature: {temp:.0f}\u00b0C.")

    if tip:
        lines += ["", f"Today\u2019s tip: {tip}"]

    lines += [
        "",
        "Share your sunset photo tonight and tag us!",
    ]

    return "\n".join(lines)


def build_evening_caption(prediction: dict, ai_rating: dict) -> str:
    """Build the Instagram caption for the evening sunset photo post."""
    predicted = prediction["score"]
    actual = ai_rating.get("ai_score", "?")

    if isinstance(actual, (int, float)) and isinstance(predicted, (int, float)):
        diff = abs(predicted - actual)
        if diff <= 0.5:
            comparison = "Spot on!"
        elif diff <= 1.5:
            comparison = "Close!"
        else:
            comparison = "The model needs more calibration data."
    else:
        comparison = ""

    lines = [
        f"Tel Aviv sunset \u2014 {actual}/10",
        "",
        f"We predicted {predicted}, the sky delivered {actual}. {comparison}",
        "",
        "See you tomorrow at noon for the next prediction.",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Post-Worthiness & Frame Selection
# ---------------------------------------------------------------------------

def should_post_evening(ai_rating) -> bool:
    """Determine if the evening sunset photo is worth posting (AI score >= 3)."""
    if not ai_rating or not isinstance(ai_rating, dict):
        return False
    score = ai_rating.get("ai_score")
    if score is None:
        return False
    return score >= 6.5


def select_best_frame(ai_rating: dict, image_dir: Path) -> Optional[Path]:
    """Select the highest-rated sunset frame from AI ratings."""
    ratings = ai_rating.get("ratings", [])
    if not ratings:
        return None

    valid = [(r["image"], r["score"]) for r in ratings
             if r.get("score") is not None]
    if not valid:
        return None

    best_name = max(valid, key=lambda x: x[1])[0]
    best_path = image_dir / best_name
    if best_path.exists():
        return best_path
    return None


# ---------------------------------------------------------------------------
# Tip Generation (Gemini)
# ---------------------------------------------------------------------------

TIP_THEMES = [
    "cocktail or drink suggestion",
    "viewing spot in Tel Aviv or nearby coast",
    "picnic snack idea",
    "music recommendation for a sunset vibe",
    "fun sunset or sky fact",
    "activity suggestion for the evening",
]


def build_tip_prompt(prediction: dict) -> str:
    """Build a prompt for Gemini to generate a contextual lifestyle tip."""
    import random
    theme = random.choice(TIP_THEMES)

    score = prediction["score"]
    condition = prediction.get("raw", {}).get("condition", "unknown")
    temp = prediction.get("comfort", {}).get("temp_c", "unknown")
    wind = prediction.get("comfort", {}).get("wind_kmh", 0)

    return (
        f"Today's sunset prediction for Tel Aviv: {score}/10. "
        f"Weather: {condition}, {temp}\u00b0C, wind {wind} km/h. "
        f"Generate a short, fun {theme} for someone about to watch the sunset. "
        f"Keep it to 1-2 sentences. Be specific and creative. "
        f"Don't mention the score or rating. Just the tip itself."
    )


def generate_tip(prediction: dict) -> Optional[str]:
    """Generate a lifestyle tip using Gemini. Returns None if unavailable."""
    try:
        import google.generativeai as genai
    except ImportError:
        log.info("google-generativeai not installed — skipping tip generation")
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.info("No GEMINI_API_KEY — skipping tip generation")
        return None

    prompt = build_tip_prompt(prediction)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt, generation_config={"max_output_tokens": 256})
        tip = response.text.strip().strip('"')
        if len(tip) > 300:
            tip = tip[:297] + "..."
        return tip
    except Exception as e:
        log.warning(f"Tip generation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Instagram Posting
# ---------------------------------------------------------------------------

def _get_ig_client():
    """Create and login to Instagram client. Returns None if credentials missing."""
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    if not username or not password:
        log.info("Instagram not configured (missing INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD)")
        return None

    try:
        from instagrapi import Client
        cl = Client()
        cl.login(username, password)
        return cl
    except Exception as e:
        log.error(f"Instagram login failed: {e}")
        return None


def post_to_instagram(image_path: Path, caption: str) -> bool:
    """Post a photo to Instagram. Returns True on success."""
    client = _get_ig_client()
    if client is None:
        return False

    try:
        client.photo_upload(str(image_path), caption)
        log.info("Instagram: photo posted")
        return True
    except Exception as e:
        log.error(f"Instagram post failed: {e}")
        return False
