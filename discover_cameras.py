"""Find and test YouTube live webcams in Israel.

Searches YouTube for live streams matching Israel/beach/webcam queries,
tests each for a working live thumbnail, and prints results. Use this
to grow the camera list in cameras.py over time.

Requires yt-dlp: pip install yt-dlp

Usage:
    python3 discover_cameras.py
    python3 discover_cameras.py --query "tel aviv sunset live cam"
"""

import argparse
import json
import subprocess
import sys

import requests

from sunset_predictor.cameras import yt_live_thumb

DEFAULT_QUERIES = [
    "israel beach live webcam camera",
    "tel aviv live camera stream",
    "israel coast webcam live",
    "חוף ישראל מצלמה לייב",
]

MIN_THUMB_SIZE = 40_000  # bytes — real frames are typically 100KB+


def find_live_streams(query: str, yt_dlp_path: str = "yt-dlp") -> list[dict]:
    """Search YouTube for live streams matching query."""
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}&sp=EgJAAQ%253D%253D"
    try:
        result = subprocess.run(
            [yt_dlp_path, "--flat-playlist", "-j", url],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        print(f"  yt-dlp not found at '{yt_dlp_path}'")
        print(f"  Install: pip install yt-dlp")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        return []

    streams = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            d = json.loads(line)
            if d.get("live_status") == "is_live":
                streams.append({
                    "id": d.get("id"),
                    "title": d.get("title", "?"),
                    "channel": d.get("uploader", "?"),
                })
        except json.JSONDecodeError:
            continue
    return streams


def test_thumbnail(video_id: str) -> tuple[bool, int]:
    """Check if a YouTube live thumbnail serves a real image."""
    url = yt_live_thumb(video_id)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200 and len(resp.content) >= MIN_THUMB_SIZE:
            return True, len(resp.content)
        return False, len(resp.content)
    except Exception:
        return False, 0


def detect_yt_dlp() -> str:
    """Find yt-dlp in common locations."""
    import shutil
    path = shutil.which("yt-dlp")
    if path:
        return path
    for candidate in [
        "/Users/amir.chowers/Library/Python/3.9/bin/yt-dlp",
        "/usr/local/bin/yt-dlp",
    ]:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, timeout=5)
            return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "yt-dlp"


def main():
    parser = argparse.ArgumentParser(description="Discover YouTube live webcams")
    parser.add_argument("--query", type=str, help="Custom search query")
    args = parser.parse_args()

    yt_dlp = detect_yt_dlp()
    queries = [args.query] if args.query else DEFAULT_QUERIES

    seen_ids = set()
    results = []

    for q in queries:
        print(f"  Searching: \"{q}\"")
        streams = find_live_streams(q, yt_dlp)
        for s in streams:
            if s["id"] in seen_ids:
                continue
            seen_ids.add(s["id"])

            works, size = test_thumbnail(s["id"])
            status = f"OK ({size // 1024}KB)" if works else f"no ({size}b)"
            print(f"    {status:>12}  {s['id']}  {s['title'][:55]}")
            if works:
                results.append(s)
    print()

    if results:
        print(f"  === {len(results)} working cameras found ===")
        print()
        for r in results:
            print(f"  Camera(")
            print(f"      name=\"{r['id'][:12]}\",")
            print(f"      image_url=yt_live_thumb(\"{r['id']}\"),")
            print(f"      direction=\"unknown\",")
            print(f"      description=\"{r['title'][:70]}\",")
            print(f"  )")
            print()
    else:
        print("  No working cameras found. Try different search queries.")


if __name__ == "__main__":
    main()
