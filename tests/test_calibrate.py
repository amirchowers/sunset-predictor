"""Tests for calibrate.py — batch Vision AI rating script."""

import json
from pathlib import Path

import pytest

from calibrate import load_manifest, save_ai_rating, find_images, parse_date


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------


class TestParseDate:

    def test_valid_date(self):
        assert parse_date("2026-02-25") == "2026-02-25"

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError):
            parse_date("not-a-date")

    def test_wrong_format_raises(self):
        with pytest.raises(ValueError):
            parse_date("25/02/2026")


# ---------------------------------------------------------------------------
# find_images
# ---------------------------------------------------------------------------


class TestFindImages:

    def test_finds_jpg_files(self, tmp_path):
        day_dir = tmp_path / "2026-02-25"
        day_dir.mkdir()
        (day_dir / "cam_sunset.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
        (day_dir / "cam_peak.jpg").write_bytes(b"\xff\xd8" + b"\x00" * 100)
        (day_dir / "predictions.json").write_text("[]")
        images = find_images(day_dir)
        assert len(images) == 2
        assert all(p.suffix == ".jpg" for p in images)

    def test_returns_empty_for_no_images(self, tmp_path):
        day_dir = tmp_path / "2026-02-25"
        day_dir.mkdir()
        (day_dir / "predictions.json").write_text("[]")
        assert find_images(day_dir) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        assert find_images(tmp_path / "nope") == []


# ---------------------------------------------------------------------------
# load_manifest / save_ai_rating
# ---------------------------------------------------------------------------


class TestManifestIO:

    def test_load_existing_manifest(self, tmp_path):
        day_dir = tmp_path / "2026-02-25"
        day_dir.mkdir()
        manifest = {"date": "2026-02-25", "ai_score": None, "predicted_score": 6.8}
        (day_dir / "manifest.json").write_text(json.dumps(manifest))
        loaded = load_manifest(day_dir)
        assert loaded["date"] == "2026-02-25"
        assert loaded["predicted_score"] == 6.8

    def test_load_missing_manifest_returns_empty(self, tmp_path):
        day_dir = tmp_path / "2026-02-25"
        day_dir.mkdir()
        loaded = load_manifest(day_dir)
        assert loaded == {}

    def test_save_ai_rating_writes_to_manifest(self, tmp_path):
        day_dir = tmp_path / "2026-02-25"
        day_dir.mkdir()
        existing = {"date": "2026-02-25", "ai_score": None, "predicted_score": 6.8, "human_score": 6.0}
        (day_dir / "manifest.json").write_text(json.dumps(existing))

        ai_result = {
            "ai_score": 7.2,
            "ratings_count": 3,
            "ratings": [
                {"image": "a.jpg", "score": 7.0, "reasoning": "nice"},
                {"image": "b.jpg", "score": 7.5, "reasoning": "great"},
                {"image": "c.jpg", "score": 7.0, "reasoning": "ok"},
            ],
        }
        save_ai_rating(day_dir, ai_result)

        saved = json.loads((day_dir / "manifest.json").read_text())
        assert saved["ai_score"] == 7.2
        assert saved["ai_ratings"] == ai_result["ratings"]
        assert saved["human_score"] == 6.0  # preserved
        assert saved["predicted_score"] == 6.8  # preserved

    def test_save_ai_rating_creates_manifest_if_missing(self, tmp_path):
        day_dir = tmp_path / "2026-02-25"
        day_dir.mkdir()
        ai_result = {"ai_score": 5.0, "ratings_count": 1, "ratings": []}
        save_ai_rating(day_dir, ai_result)
        saved = json.loads((day_dir / "manifest.json").read_text())
        assert saved["ai_score"] == 5.0
