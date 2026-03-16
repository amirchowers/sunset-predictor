"""Vision AI sunset rater — Gemini primary, HuggingFace fallback.

Sends captured webcam images to a Vision AI model and asks for a 1-10 sunset
quality rating. Tries Gemini first; on quota/auth errors, falls back to
HuggingFace Inference API (GLM-4.5V via auto-routed provider).
"""

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger("rater")

HF_MODEL = "zai-org/GLM-4.5V"
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"

def _parse_rating_response(response_text: str) -> dict:
    """Parse a Vision AI response into {score, reasoning}. Shared by all backends."""
    text = response_text.strip()
    if not text:
        return {"score": None, "reasoning": "Failed to parse: empty response"}

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        result = json.loads(text)
        if "score" not in result:
            return {"score": None, "reasoning": f"Failed to parse: missing 'score' key in {text}"}
        result["score"] = round(float(result["score"]), 1)
        result.setdefault("reasoning", "")
        return result
    except (json.JSONDecodeError, ValueError):
        pass

    match = re.search(r'\{[^{}]*"score"\s*:\s*[\d.]+[^{}]*\}', text)
    if match:
        try:
            result = json.loads(match.group())
            result["score"] = round(float(result["score"]), 1)
            result.setdefault("reasoning", "")
            return result
        except (json.JSONDecodeError, ValueError):
            pass

    return {"score": None, "reasoning": f"Failed to parse: {text}"}


RATING_PROMPT = """You are an expert sunset photographer and meteorologist.

Rate this sunset webcam image on a 1-10 scale based on:
- Sky colors (vivid reds, oranges, purples = higher)
- Sun visibility (visible sun touching/near horizon = higher)
- Cloud drama (illuminated clouds catching color = higher)
- Overall beauty and atmosphere

Important context:
- These are low-resolution (640x480) webcam frames from Israeli Mediterranean beaches
- The camera faces west over the sea
- A score of 1 means terrible (overcast, no color, no sun visible)
- A score of 5 means average (sun visible but no dramatic colors)
- A score of 8+ means spectacular (vivid multi-color sky, dramatic clouds lit up)
- If the image is clearly not showing a sunset (daytime, night, or camera offline), score it 1

Respond with ONLY a JSON object, no other text:
{"score": <float 1-10>, "reasoning": "<one sentence>"}"""


def rate_single_image_gemini(image_path: Path, api_key: Optional[str] = None) -> dict:
    """Rate a single sunset image using Gemini Vision."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")

    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment or .env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    img_data = image_path.read_bytes()
    suffix = image_path.suffix.lower()
    mime_type = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"

    response = model.generate_content(
        [
            {"mime_type": mime_type, "data": img_data},
            RATING_PROMPT,
        ],
        generation_config={"max_output_tokens": 1024},
    )

    return _parse_rating_response(response.text)


def rate_single_image(image_path: Path) -> dict:
    """Rate a sunset image — tries Gemini first, falls back to HuggingFace."""
    try:
        result = rate_single_image_gemini(image_path)
        if result.get("score") is not None:
            return result
        log.info("Gemini returned no score, trying HuggingFace fallback")
    except Exception as e:
        log.info(f"Gemini failed ({e}), trying HuggingFace fallback")

    try:
        return rate_single_image_huggingface(image_path)
    except Exception as e:
        return {"score": None, "reasoning": f"Error: both backends failed — {e}"}


def rate_single_image_huggingface(image_path: Path, api_key: Optional[str] = None) -> dict:
    """Rate a single sunset image using HuggingFace Inference API."""
    api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        raise RuntimeError("HUGGINGFACE_API_KEY not set in environment or .env")

    img_data = image_path.read_bytes()
    b64 = base64.b64encode(img_data).decode("utf-8")
    suffix = image_path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"

    payload = {
        "model": HF_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": RATING_PROMPT},
                ],
            }
        ],
        "max_tokens": 500,
    }

    try:
        resp = requests.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]
        content = message.get("content", "").strip()
        if not content:
            content = message.get("reasoning_content", "").strip()
        return _parse_rating_response(content)
    except Exception as e:
        return {"score": None, "reasoning": f"Error: {e}"}


def rate_sunset_images(image_paths: list) -> dict:
    """Rate multiple sunset images and return aggregate + per-image scores."""
    ratings = []
    for path in image_paths:
        p = Path(path) if not isinstance(path, Path) else path
        if not p.exists():
            continue
        try:
            rating = rate_single_image(p)
            rating["image"] = p.name
            ratings.append(rating)
        except Exception as e:
            ratings.append({"image": p.name, "score": None, "reasoning": f"Error: {e}"})

    valid_scores = [r["score"] for r in ratings if r["score"] is not None]
    avg_score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

    return {
        "ai_score": avg_score,
        "ratings_count": len(valid_scores),
        "ratings": ratings,
    }
