"""Tests for sunset_predictor/rater.py — response parsing, fallback logic, aggregation."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sunset_predictor.rater import (
    _parse_rating_response,
    rate_single_image_huggingface,
    rate_single_image,
    rate_sunset_images,
)


# ---------------------------------------------------------------------------
# _parse_rating_response
# ---------------------------------------------------------------------------


class TestParseRatingResponse:
    """Test the shared JSON parsing for both Gemini and HuggingFace responses."""

    def test_valid_json(self):
        raw = '{"score": 7.5, "reasoning": "Beautiful orange sky with clouds"}'
        result = _parse_rating_response(raw)
        assert result["score"] == 7.5
        assert result["reasoning"] == "Beautiful orange sky with clouds"

    def test_score_rounded_to_one_decimal(self):
        raw = '{"score": 7.456, "reasoning": "test"}'
        result = _parse_rating_response(raw)
        assert result["score"] == 7.5

    def test_score_as_string_converted_to_float(self):
        raw = '{"score": "8.2", "reasoning": "test"}'
        result = _parse_rating_response(raw)
        assert result["score"] == 8.2

    def test_score_as_integer(self):
        raw = '{"score": 6, "reasoning": "average"}'
        result = _parse_rating_response(raw)
        assert result["score"] == 6.0

    def test_markdown_wrapped_json(self):
        raw = '```json\n{"score": 7.5, "reasoning": "test"}\n```'
        result = _parse_rating_response(raw)
        assert result["score"] == 7.5
        assert result["reasoning"] == "test"

    def test_markdown_wrapped_no_language_tag(self):
        raw = '```\n{"score": 4.0, "reasoning": "overcast"}\n```'
        result = _parse_rating_response(raw)
        assert result["score"] == 4.0

    def test_malformed_json_returns_none_score(self):
        raw = "this is not json at all"
        result = _parse_rating_response(raw)
        assert result["score"] is None
        assert "Failed to parse" in result["reasoning"]

    def test_missing_score_key_returns_none(self):
        raw = '{"reasoning": "no score field"}'
        result = _parse_rating_response(raw)
        assert result["score"] is None

    def test_missing_reasoning_key_still_returns_score(self):
        raw = '{"score": 5.0}'
        result = _parse_rating_response(raw)
        assert result["score"] == 5.0
        assert result["reasoning"] == ""

    def test_empty_string_returns_none_score(self):
        raw = ""
        result = _parse_rating_response(raw)
        assert result["score"] is None

    def test_whitespace_around_json(self):
        raw = '  \n  {"score": 9.0, "reasoning": "spectacular"}  \n  '
        result = _parse_rating_response(raw)
        assert result["score"] == 9.0

    def test_score_out_of_range_still_parsed(self):
        """Parsing doesn't enforce 1-10 range — that's a higher-level concern."""
        raw = '{"score": 15.0, "reasoning": "impossible"}'
        result = _parse_rating_response(raw)
        assert result["score"] == 15.0

    def test_json_embedded_in_text(self):
        raw = 'Here is my rating:\n{"score": 7.0, "reasoning": "nice sunset"}\nThat is my answer.'
        result = _parse_rating_response(raw)
        assert result["score"] == 7.0
        assert result["reasoning"] == "nice sunset"

    def test_json_with_leading_newline(self):
        raw = '\n{"score": 8.0, "reasoning": "vivid colors"}'
        result = _parse_rating_response(raw)
        assert result["score"] == 8.0


# ---------------------------------------------------------------------------
# rate_single_image_huggingface
# ---------------------------------------------------------------------------


class TestRateSingleImageHuggingface:
    """Test HuggingFace Inference API integration (mocked HTTP)."""

    @pytest.fixture
    def fake_image(self, tmp_path):
        img = tmp_path / "sunset.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        return img

    def _mock_hf_response(self, content_text, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": content_text}}]
        }
        mock_resp.raise_for_status = MagicMock()
        if status_code >= 400:
            from requests.exceptions import HTTPError
            mock_resp.raise_for_status.side_effect = HTTPError(
                f"{status_code} Error", response=mock_resp
            )
        return mock_resp

    @patch("sunset_predictor.rater.requests.post")
    def test_successful_rating(self, mock_post, fake_image):
        mock_post.return_value = self._mock_hf_response(
            '{"score": 7.5, "reasoning": "Vivid orange sky"}'
        )
        result = rate_single_image_huggingface(fake_image, api_key="hf_test")
        assert result["score"] == 7.5
        assert result["reasoning"] == "Vivid orange sky"

    @patch("sunset_predictor.rater.requests.post")
    def test_sends_correct_payload_structure(self, mock_post, fake_image):
        mock_post.return_value = self._mock_hf_response(
            '{"score": 5.0, "reasoning": "average"}'
        )
        rate_single_image_huggingface(fake_image, api_key="hf_test")
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "messages" in payload
        msg = payload["messages"][0]
        assert msg["role"] == "user"
        content_types = [c["type"] for c in msg["content"]]
        assert "image_url" in content_types
        assert "text" in content_types

    @patch("sunset_predictor.rater.requests.post")
    def test_sends_auth_header(self, mock_post, fake_image):
        mock_post.return_value = self._mock_hf_response(
            '{"score": 5.0, "reasoning": "ok"}'
        )
        rate_single_image_huggingface(fake_image, api_key="hf_test_key")
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["Authorization"] == "Bearer hf_test_key"

    @patch("sunset_predictor.rater.requests.post")
    def test_http_error_returns_none_score(self, mock_post, fake_image):
        mock_post.return_value = self._mock_hf_response("", status_code=500)
        result = rate_single_image_huggingface(fake_image, api_key="hf_test")
        assert result["score"] is None
        assert "Error" in result["reasoning"]

    @patch("sunset_predictor.rater.requests.post")
    def test_malformed_response_returns_none_score(self, mock_post, fake_image):
        mock_post.return_value = self._mock_hf_response("not json at all")
        result = rate_single_image_huggingface(fake_image, api_key="hf_test")
        assert result["score"] is None

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_raises(self, fake_image):
        with pytest.raises(RuntimeError, match="HUGGINGFACE_API_KEY"):
            rate_single_image_huggingface(fake_image, api_key=None)


# ---------------------------------------------------------------------------
# Fallback logic: rate_single_image tries Gemini, then HuggingFace
# ---------------------------------------------------------------------------


class TestFallbackLogic:
    """rate_single_image should try Gemini first, fall back to HuggingFace on failure."""

    @pytest.fixture
    def fake_image(self, tmp_path):
        img = tmp_path / "sunset.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        return img

    @patch("sunset_predictor.rater.rate_single_image_gemini")
    def test_gemini_success_skips_huggingface(self, mock_gemini, fake_image):
        mock_gemini.return_value = {"score": 8.0, "reasoning": "Gemini says great"}
        result = rate_single_image(fake_image)
        assert result["score"] == 8.0
        assert result["reasoning"] == "Gemini says great"

    @patch("sunset_predictor.rater.rate_single_image_huggingface")
    @patch("sunset_predictor.rater.rate_single_image_gemini")
    def test_gemini_fails_falls_back_to_huggingface(self, mock_gemini, mock_hf, fake_image):
        mock_gemini.side_effect = RuntimeError("429 quota exceeded")
        mock_hf.return_value = {"score": 6.5, "reasoning": "HuggingFace fallback"}
        result = rate_single_image(fake_image)
        assert result["score"] == 6.5
        mock_hf.assert_called_once()

    @patch("sunset_predictor.rater.rate_single_image_huggingface")
    @patch("sunset_predictor.rater.rate_single_image_gemini")
    def test_both_fail_returns_error(self, mock_gemini, mock_hf, fake_image):
        mock_gemini.side_effect = RuntimeError("Gemini error")
        mock_hf.side_effect = RuntimeError("HuggingFace error")
        result = rate_single_image(fake_image)
        assert result["score"] is None
        assert "Error" in result["reasoning"]

    @patch("sunset_predictor.rater.rate_single_image_gemini")
    def test_no_gemini_key_skips_to_huggingface(self, mock_gemini, fake_image):
        """When Gemini raises RuntimeError for missing key, fallback should fire."""
        mock_gemini.side_effect = RuntimeError("GEMINI_API_KEY not set")
        with patch("sunset_predictor.rater.rate_single_image_huggingface") as mock_hf:
            mock_hf.return_value = {"score": 7.0, "reasoning": "HF works"}
            result = rate_single_image(fake_image)
            assert result["score"] == 7.0


# ---------------------------------------------------------------------------
# rate_sunset_images — aggregation
# ---------------------------------------------------------------------------


class TestRateSunsetImages:
    """Test multi-image aggregation logic."""

    @pytest.fixture
    def fake_images(self, tmp_path):
        paths = []
        for i in range(3):
            p = tmp_path / f"img_{i}.jpg"
            p.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            paths.append(p)
        return paths

    @patch("sunset_predictor.rater.rate_single_image")
    def test_averages_valid_scores(self, mock_rate, fake_images):
        mock_rate.side_effect = [
            {"score": 6.0, "reasoning": "a"},
            {"score": 8.0, "reasoning": "b"},
            {"score": 7.0, "reasoning": "c"},
        ]
        result = rate_sunset_images(fake_images)
        assert result["ai_score"] == 7.0
        assert result["ratings_count"] == 3

    @patch("sunset_predictor.rater.rate_single_image")
    def test_skips_none_scores_in_average(self, mock_rate, fake_images):
        mock_rate.side_effect = [
            {"score": 6.0, "reasoning": "ok"},
            {"score": None, "reasoning": "failed"},
            {"score": 8.0, "reasoning": "great"},
        ]
        result = rate_sunset_images(fake_images)
        assert result["ai_score"] == 7.0
        assert result["ratings_count"] == 2

    @patch("sunset_predictor.rater.rate_single_image")
    def test_all_failures_returns_none(self, mock_rate, fake_images):
        mock_rate.side_effect = [
            {"score": None, "reasoning": "fail"},
            {"score": None, "reasoning": "fail"},
            {"score": None, "reasoning": "fail"},
        ]
        result = rate_sunset_images(fake_images)
        assert result["ai_score"] is None
        assert result["ratings_count"] == 0

    @patch("sunset_predictor.rater.rate_single_image")
    def test_per_image_ratings_include_filename(self, mock_rate, fake_images):
        mock_rate.side_effect = [
            {"score": 5.0, "reasoning": "ok"},
            {"score": 5.0, "reasoning": "ok"},
            {"score": 5.0, "reasoning": "ok"},
        ]
        result = rate_sunset_images(fake_images)
        filenames = [r["image"] for r in result["ratings"]]
        assert filenames == ["img_0.jpg", "img_1.jpg", "img_2.jpg"]

    def test_nonexistent_images_skipped(self, tmp_path):
        paths = [tmp_path / "does_not_exist.jpg"]
        result = rate_sunset_images(paths)
        assert result["ai_score"] is None
        assert result["ratings"] == []
