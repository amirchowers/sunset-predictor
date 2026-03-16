"""Tests for sunset_predictor/poster.py — card generation, captions, overlay, post logic."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_prediction():
    return {
        "score": 7.2,
        "verdict": "Worth making plans for",
        "scores": {
            "cloud_high": 8.0,
            "cloud_low_mid": 7.0,
            "western_near": 9.0,
            "western_far": 6.0,
            "humidity": 6.0,
            "visibility": 10.0,
            "air_quality": 7.0,
            "weather_condition": 8.0,
        },
        "raw": {
            "cloud_cover_pct": 35,
            "humidity_pct": 55,
            "visibility_km": 25.0,
            "pm2_5": 18.0,
            "condition": "scattered clouds",
            "condition_id": 802,
            "western_near_clouds_pct": 40,
            "western_far_clouds_pct": 55,
            "cloud_high_pct": 30,
            "cloud_mid_pct": 10,
            "cloud_low_pct": 5,
        },
        "sunset_local": "17:42",
        "comfort": {
            "temp_c": 22.0,
            "feels_like_c": 21.0,
            "wind_kmh": 12.0,
            "wind_gusts_kmh": 20.0,
        },
    }


@pytest.fixture
def sample_prediction_low():
    return {
        "score": 2.8,
        "verdict": "Skip it",
        "scores": {
            "cloud_high": 2.0,
            "cloud_low_mid": 1.0,
            "western_near": 1.0,
            "western_far": 2.0,
            "humidity": 3.0,
            "visibility": 5.0,
            "air_quality": 4.0,
            "weather_condition": 2.0,
        },
        "raw": {
            "cloud_cover_pct": 95,
            "humidity_pct": 85,
            "visibility_km": 5.0,
            "pm2_5": 60.0,
            "condition": "overcast",
            "condition_id": 804,
            "western_near_clouds_pct": 95,
            "western_far_clouds_pct": 90,
            "cloud_high_pct": 0,
            "cloud_mid_pct": 70,
            "cloud_low_pct": 80,
        },
        "sunset_local": "17:42",
        "comfort": {
            "temp_c": 14.0,
            "feels_like_c": 11.0,
            "wind_kmh": 35.0,
            "wind_gusts_kmh": 50.0,
        },
    }


@pytest.fixture
def sample_sunset_image(tmp_path):
    img = Image.new("RGB", (640, 480), color=(255, 140, 50))
    path = tmp_path / "ashdod_arches_t1527.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture
def sample_ai_rating():
    return {
        "ai_score": 6.5,
        "ratings_count": 1,
        "ratings": [
            {
                "score": 6.5,
                "reasoning": "Warm orange glow, sun on horizon, lacks dramatic clouds.",
                "image": "ashdod_arches_t1527.jpg",
            }
        ],
    }


# ---------------------------------------------------------------------------
# Card Generation
# ---------------------------------------------------------------------------

class TestGeneratePredictionCard:
    def test_card_dimensions(self, sample_prediction):
        from sunset_predictor.poster import generate_prediction_card
        img = generate_prediction_card(sample_prediction, tip="Grab an Aperol Spritz.")
        assert img.size == (1080, 1080)

    def test_card_is_rgb(self, sample_prediction):
        from sunset_predictor.poster import generate_prediction_card
        img = generate_prediction_card(sample_prediction, tip="Test tip.")
        assert img.mode == "RGB"

    def test_card_without_tip(self, sample_prediction):
        from sunset_predictor.poster import generate_prediction_card
        img = generate_prediction_card(sample_prediction, tip=None)
        assert img.size == (1080, 1080)

    def test_card_low_score(self, sample_prediction_low):
        from sunset_predictor.poster import generate_prediction_card
        img = generate_prediction_card(sample_prediction_low, tip="Stay home tonight.")
        assert img.size == (1080, 1080)


# ---------------------------------------------------------------------------
# Score Overlay
# ---------------------------------------------------------------------------

class TestScoreOverlay:
    def test_overlay_dimensions_match_input(self, sample_sunset_image):
        from sunset_predictor.poster import overlay_score
        img = overlay_score(sample_sunset_image, score=6.5, verdict="Worth making plans for")
        assert img.size == (640, 480)

    def test_overlay_is_rgb(self, sample_sunset_image):
        from sunset_predictor.poster import overlay_score
        img = overlay_score(sample_sunset_image, score=6.5, verdict="Worth making plans for")
        assert img.mode == "RGB"

    def test_overlay_modifies_image(self, sample_sunset_image):
        from sunset_predictor.poster import overlay_score
        original = Image.open(sample_sunset_image)
        original_pixels = list(original.getdata())
        overlaid = overlay_score(sample_sunset_image, score=8.0, verdict="Tell your friends")
        overlaid_pixels = list(overlaid.getdata())
        assert original_pixels != overlaid_pixels


# ---------------------------------------------------------------------------
# Noon Caption
# ---------------------------------------------------------------------------

class TestBuildNoonCaption:
    def test_caption_contains_score(self, sample_prediction):
        from sunset_predictor.poster import build_noon_caption
        caption = build_noon_caption(sample_prediction, tip="Grab an Aperol Spritz.")
        assert "7.2" in caption

    def test_caption_contains_verdict(self, sample_prediction):
        from sunset_predictor.poster import build_noon_caption
        caption = build_noon_caption(sample_prediction, tip="Test tip.")
        assert "Worth making plans for" in caption

    def test_caption_contains_sunset_time(self, sample_prediction):
        from sunset_predictor.poster import build_noon_caption
        caption = build_noon_caption(sample_prediction, tip="Test tip.")
        assert "17:42" in caption

    def test_caption_contains_tip(self, sample_prediction):
        from sunset_predictor.poster import build_noon_caption
        caption = build_noon_caption(sample_prediction, tip="Bring a blanket and hot cocoa.")
        assert "Bring a blanket and hot cocoa." in caption

    def test_caption_without_tip(self, sample_prediction):
        from sunset_predictor.poster import build_noon_caption
        caption = build_noon_caption(sample_prediction, tip=None)
        assert "7.2" in caption

    def test_caption_has_share_cta(self, sample_prediction):
        from sunset_predictor.poster import build_noon_caption
        caption = build_noon_caption(sample_prediction, tip=None)
        assert "share" in caption.lower() or "tag" in caption.lower()

    def test_caption_under_2200_chars(self, sample_prediction):
        """Instagram caption limit is 2200 characters."""
        from sunset_predictor.poster import build_noon_caption
        caption = build_noon_caption(sample_prediction, tip="A" * 200)
        assert len(caption) <= 2200


# ---------------------------------------------------------------------------
# Evening Caption
# ---------------------------------------------------------------------------

class TestBuildEveningCaption:
    def test_caption_contains_predicted_and_actual(self, sample_prediction, sample_ai_rating):
        from sunset_predictor.poster import build_evening_caption
        caption = build_evening_caption(sample_prediction, sample_ai_rating)
        assert "7.2" in caption
        assert "6.5" in caption

    def test_caption_under_2200_chars(self, sample_prediction, sample_ai_rating):
        from sunset_predictor.poster import build_evening_caption
        caption = build_evening_caption(sample_prediction, sample_ai_rating)
        assert len(caption) <= 2200


# ---------------------------------------------------------------------------
# Post-Worthiness Logic
# ---------------------------------------------------------------------------

class TestShouldPostEvening:
    def test_high_score_qualifies(self, sample_ai_rating):
        from sunset_predictor.poster import should_post_evening
        assert should_post_evening(sample_ai_rating) is True

    def test_low_score_rejected(self):
        from sunset_predictor.poster import should_post_evening
        rating = {"ai_score": 5.0, "ratings_count": 1, "ratings": []}
        assert should_post_evening(rating) is False

    def test_no_rating_rejected(self):
        from sunset_predictor.poster import should_post_evening
        assert should_post_evening({}) is False
        assert should_post_evening(None) is False

    def test_boundary_score_6_5_qualifies(self):
        from sunset_predictor.poster import should_post_evening
        rating = {"ai_score": 6.5, "ratings_count": 1, "ratings": []}
        assert should_post_evening(rating) is True

    def test_score_just_below_6_5_rejected(self):
        from sunset_predictor.poster import should_post_evening
        rating = {"ai_score": 6.4, "ratings_count": 1, "ratings": []}
        assert should_post_evening(rating) is False


# ---------------------------------------------------------------------------
# Best Frame Selection
# ---------------------------------------------------------------------------

class TestSelectBestFrame:
    def test_selects_highest_scored(self, tmp_path):
        from sunset_predictor.poster import select_best_frame
        for name in ["a.jpg", "b.jpg", "c.jpg"]:
            Image.new("RGB", (640, 480)).save(tmp_path / name)
        ratings = {
            "ratings": [
                {"image": "a.jpg", "score": 4.0},
                {"image": "b.jpg", "score": 7.5},
                {"image": "c.jpg", "score": 5.0},
            ]
        }
        best = select_best_frame(ratings, tmp_path)
        assert best.name == "b.jpg"

    def test_skips_null_scores(self, tmp_path):
        from sunset_predictor.poster import select_best_frame
        for name in ["a.jpg", "b.jpg"]:
            Image.new("RGB", (640, 480)).save(tmp_path / name)
        ratings = {
            "ratings": [
                {"image": "a.jpg", "score": None},
                {"image": "b.jpg", "score": 5.0},
            ]
        }
        best = select_best_frame(ratings, tmp_path)
        assert best.name == "b.jpg"

    def test_returns_none_when_all_null(self, tmp_path):
        from sunset_predictor.poster import select_best_frame
        ratings = {
            "ratings": [
                {"image": "a.jpg", "score": None},
            ]
        }
        assert select_best_frame(ratings, tmp_path) is None

    def test_returns_none_on_empty(self, tmp_path):
        from sunset_predictor.poster import select_best_frame
        assert select_best_frame({"ratings": []}, tmp_path) is None
        assert select_best_frame({}, tmp_path) is None


# ---------------------------------------------------------------------------
# Tip Prompt Assembly
# ---------------------------------------------------------------------------

class TestBuildTipPrompt:
    def test_prompt_contains_score(self, sample_prediction):
        from sunset_predictor.poster import build_tip_prompt
        prompt = build_tip_prompt(sample_prediction)
        assert "7.2" in prompt

    def test_prompt_contains_weather_context(self, sample_prediction):
        from sunset_predictor.poster import build_tip_prompt
        prompt = build_tip_prompt(sample_prediction)
        assert "scattered clouds" in prompt.lower() or "22" in prompt

    def test_prompt_requests_short_response(self, sample_prediction):
        from sunset_predictor.poster import build_tip_prompt
        prompt = build_tip_prompt(sample_prediction)
        assert "sentence" in prompt.lower() or "short" in prompt.lower() or "brief" in prompt.lower()


# ---------------------------------------------------------------------------
# Instagram Posting (mocked)
# ---------------------------------------------------------------------------

class TestPostToInstagram:
    @patch("sunset_predictor.poster._get_ig_client")
    def test_post_photo_calls_upload(self, mock_client, sample_sunset_image):
        from sunset_predictor.poster import post_to_instagram
        client = MagicMock()
        mock_client.return_value = client
        client.photo_upload.return_value = MagicMock(pk="123")

        result = post_to_instagram(sample_sunset_image, "Test caption")
        assert result is True
        client.photo_upload.assert_called_once()

    @patch("sunset_predictor.poster._get_ig_client")
    def test_post_returns_false_on_failure(self, mock_client, sample_sunset_image):
        from sunset_predictor.poster import post_to_instagram
        client = MagicMock()
        mock_client.return_value = client
        client.photo_upload.side_effect = Exception("Auth failed")

        result = post_to_instagram(sample_sunset_image, "Test caption")
        assert result is False

    def test_post_skips_when_no_credentials(self, sample_sunset_image):
        from sunset_predictor.poster import post_to_instagram
        with patch.dict("os.environ", {}, clear=True):
            with patch("sunset_predictor.poster._get_ig_client", return_value=None):
                result = post_to_instagram(sample_sunset_image, "Test caption")
                assert result is False
