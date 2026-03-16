"""Telegram notification module for sunset predictions.

Uses the Telegram Bot HTTP API directly via requests (no extra dependency).
Setup: create a bot via @BotFather, get the token, send it a message,
then grab your chat_id from https://api.telegram.org/bot<TOKEN>/getUpdates.
"""

import logging
import os

import requests
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

log = logging.getLogger("notifier")

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _get_config() -> tuple:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    return token, chat_id


def _score_bar(score: float, width: int = 10) -> str:
    filled = int(round(score / 10 * width))
    return "\u2588" * filled + "\u2591" * (width - filled)


def _comfort_warnings(comfort) -> list:
    if not comfort:
        return []
    warnings = []
    wind = comfort.get("wind_kmh", 0)
    gusts = comfort.get("wind_gusts_kmh", 0)
    temp = comfort.get("temp_c", 20)
    feels = comfort.get("feels_like_c", temp)

    if wind >= 40:
        warnings.append(f"\U0001f4a8 Very windy: {wind:.0f} km/h (gusts {gusts:.0f})")
    elif wind >= 25:
        warnings.append(f"\U0001f4a8 Windy: {wind:.0f} km/h (gusts {gusts:.0f})")

    if feels < 8:
        warnings.append(f"\U0001f9e5 Cold: {temp:.0f}\u00b0C (feels {feels:.0f}\u00b0C)")
    elif feels < 15:
        warnings.append(f"\U0001f9e5 Cool: {temp:.0f}\u00b0C (feels {feels:.0f}\u00b0C)")

    return warnings


def format_message(result: dict, verdict: str, sun_info: dict, location) -> str:
    sunset_local = sun_info["sunset"].astimezone(ZoneInfo(location.timezone))
    date_str = sunset_local.strftime("%A, %b %d")
    time_str = sunset_local.strftime("%H:%M")

    overall = result["overall"]
    scores = result["scores"]
    raw = result["raw"]
    has_layers = result.get("has_cloud_layers", False)

    lines = [
        f"\U0001f305 *Sunset Prediction \u2014 {location.name}*",
        f"{date_str}",
        "",
        f"*{overall}/10*  {_score_bar(overall)}",
        f"_{verdict}_",
        "",
    ]

    if has_layers:
        lines.append(f"\u2601\ufe0f High clouds: {raw['cloud_high_pct']}% \u2192 {scores['cloud_high']:.0f}/10")
        lines.append(f"\u2601\ufe0f Low/mid: {raw['cloud_low_pct']}%/{raw['cloud_mid_pct']}% \u2192 {scores['cloud_low_mid']:.0f}/10")
    else:
        lines.append(f"\u2601\ufe0f Clouds: {raw['cloud_cover_pct']}% \u2192 {scores['cloud_cover']:.0f}/10")

    lines += [
        f"\U0001f9ed West (near): {raw['western_near_clouds_pct']}% \u2192 {scores['western_near']:.0f}/10",
        f"\U0001f9ed West (far): {raw['western_far_clouds_pct']}% \u2192 {scores['western_far']:.0f}/10",
        f"\U0001f4a7 Humidity: {raw['humidity_pct']}% \u2192 {scores['humidity']:.0f}/10",
        f"\U0001f441 Visibility: {raw['visibility_km']} km \u2192 {scores['visibility']:.0f}/10",
        f"\U0001f32b Air quality: PM2.5 {raw['pm2_5']} \u2192 {scores['air_quality']:.0f}/10",
        f"\u26c5 {raw['condition']} \u2192 {scores['weather_condition']:.0f}/10",
        "",
        f"\U0001f307 Sunset at *{time_str}*",
    ]

    comfort = result["raw"].get("comfort")
    warnings = _comfort_warnings(comfort)
    if warnings:
        lines.append("")
        lines.extend(warnings)

    return "\n".join(lines)


def send_prediction(result: dict, verdict: str, sun_info: dict, location) -> bool:
    """Send sunset prediction to Telegram. Returns True on success."""
    token, chat_id = _get_config()
    if not token or not chat_id:
        log.info("Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
        return False

    text = format_message(result, verdict, sun_info, location)
    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }, timeout=15)

    if resp.ok:
        log.info("Telegram: prediction sent")
    else:
        log.error(f"Telegram sendMessage failed: {resp.status_code} {resp.text}")
    return resp.ok
