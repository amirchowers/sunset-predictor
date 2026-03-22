"""Tests for sunset_predictor/renderer.py — helper functions and driver logic."""

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def high_score_prediction():
    """Score 8.2 — drivers should be positive, top-scoring factors."""
    return {
        "score": 8.2,
        "verdict": "Tell your friends — rare show",
        "scores": {
            "cloud_high": 10.0,
            "cloud_low_mid": 9.0,
            "western_near": 10.0,
            "western_far": 8.0,
            "humidity": 8.0,
            "visibility": 10.0,
            "air_quality": 7.0,
            "weather_condition": 10.0,
        },
    }


@pytest.fixture
def low_score_prediction():
    """Score 2.8 — drivers should be negative, lowest-scoring factors."""
    return {
        "score": 2.8,
        "verdict": "Skip it",
        "scores": {
            "cloud_high": 3.0,
            "cloud_low_mid": 1.0,
            "western_near": 1.0,
            "western_far": 2.0,
            "humidity": 3.0,
            "visibility": 5.0,
            "air_quality": 4.0,
            "weather_condition": 2.0,
        },
    }


@pytest.fixture
def mid_score_prediction():
    """Score 5.5 — at/above threshold, drivers should be positive."""
    return {
        "score": 5.5,
        "verdict": "Watchable — sun meets the sea",
        "scores": {
            "cloud_high": 7.0,
            "cloud_low_mid": 5.0,
            "western_near": 5.0,
            "western_far": 6.0,
            "humidity": 6.0,
            "visibility": 8.0,
            "air_quality": 5.0,
            "weather_condition": 6.0,
        },
    }


# ---------------------------------------------------------------------------
# _top_drivers — positive phrasing for high scores
# ---------------------------------------------------------------------------

class TestTopDriversHighScore:
    def test_returns_two_drivers_by_default(self, high_score_prediction):
        from sunset_predictor.renderer import _top_drivers
        drivers = _top_drivers(high_score_prediction)
        assert len(drivers) == 2

    def test_returns_positive_phrasing(self, high_score_prediction):
        from sunset_predictor.renderer import _top_drivers
        drivers = _top_drivers(high_score_prediction)
        for d in drivers:
            assert d[0].islower() or d[0].isupper()
            assert "blocked" not in d
            assert "heavy" not in d
            assert "poor" not in d
            assert "no " not in d

    def test_returns_highest_scoring_factors(self, high_score_prediction):
        from sunset_predictor.renderer import _top_drivers
        drivers = _top_drivers(high_score_prediction, n=2)
        # cloud_high=10, western_near=10, weather_condition=10 are tied at top
        # Any two of these are correct
        positive_top = {"high cirrus clouds", "clear western horizon", "ideal weather"}
        assert set(drivers).issubset(positive_top)

    def test_mid_score_uses_positive_phrasing(self, mid_score_prediction):
        from sunset_predictor.renderer import _top_drivers
        drivers = _top_drivers(mid_score_prediction)
        for d in drivers:
            assert "blocked" not in d
            assert "heavy" not in d


# ---------------------------------------------------------------------------
# _top_drivers — negative phrasing for low scores
# ---------------------------------------------------------------------------

class TestTopDriversLowScore:
    def test_returns_negative_phrasing(self, low_score_prediction):
        from sunset_predictor.renderer import _top_drivers
        drivers = _top_drivers(low_score_prediction)
        from sunset_predictor.scorer import FACTOR_LABELS_LOW
        assert all(d in FACTOR_LABELS_LOW.values() for d in drivers)

    def test_returns_lowest_scoring_factors(self, low_score_prediction):
        from sunset_predictor.renderer import _top_drivers
        drivers = _top_drivers(low_score_prediction, n=2)
        # cloud_low_mid=1.0 and western_near=1.0 are the lowest
        from sunset_predictor.scorer import FACTOR_LABELS_LOW
        expected_keys = {"cloud_low_mid", "western_near"}
        expected_labels = {FACTOR_LABELS_LOW[k] for k in expected_keys}
        assert set(drivers) == expected_labels

    def test_threshold_at_5(self):
        """Score exactly 5.0 should use positive phrasing (>= 5.0 is positive)."""
        from sunset_predictor.renderer import _top_drivers
        pred = {
            "score": 5.0,
            "scores": {
                "cloud_high": 5.0,
                "cloud_low_mid": 3.0,
                "western_near": 7.0,
                "western_far": 5.0,
                "humidity": 5.0,
                "visibility": 5.0,
                "air_quality": 5.0,
                "weather_condition": 5.0,
            },
        }
        drivers = _top_drivers(pred)
        assert "blocked" not in drivers[0]

    def test_score_4_9_uses_negative(self):
        """Score 4.9 should use negative phrasing (< 5.0)."""
        from sunset_predictor.renderer import _top_drivers
        pred = {
            "score": 4.9,
            "scores": {
                "cloud_high": 4.0,
                "cloud_low_mid": 1.0,
                "western_near": 3.0,
                "western_far": 5.0,
                "humidity": 6.0,
                "visibility": 8.0,
                "air_quality": 5.0,
                "weather_condition": 3.0,
            },
        }
        drivers = _top_drivers(pred, n=2)
        from sunset_predictor.scorer import FACTOR_LABELS_LOW
        assert all(d in FACTOR_LABELS_LOW.values() for d in drivers)


# ---------------------------------------------------------------------------
# _lerp_color
# ---------------------------------------------------------------------------

class TestLerpColor:
    def test_score_1_returns_lowest_anchor(self):
        from sunset_predictor.renderer import _lerp_color, _load_tokens
        tokens = _load_tokens()
        anchors = tokens["color"]["accent"]["anchors"]
        result = _lerp_color(1.0, anchors)
        assert result.lower() == anchors[0]["hex"].lower()

    def test_score_10_returns_highest_anchor(self):
        from sunset_predictor.renderer import _lerp_color, _load_tokens
        tokens = _load_tokens()
        anchors = tokens["color"]["accent"]["anchors"]
        result = _lerp_color(10.0, anchors)
        assert result.lower() == anchors[-1]["hex"].lower()

    def test_returns_valid_hex(self):
        from sunset_predictor.renderer import _lerp_color, _load_tokens
        tokens = _load_tokens()
        anchors = tokens["color"]["accent"]["anchors"]
        for score in [1.0, 3.5, 5.0, 7.6, 10.0]:
            result = _lerp_color(score, anchors)
            assert result.startswith("#")
            assert len(result) == 7

    def test_clamped_below_1(self):
        from sunset_predictor.renderer import _lerp_color, _load_tokens
        tokens = _load_tokens()
        anchors = tokens["color"]["accent"]["anchors"]
        assert _lerp_color(0.0, anchors) == _lerp_color(1.0, anchors)

    def test_clamped_above_10(self):
        from sunset_predictor.renderer import _lerp_color, _load_tokens
        tokens = _load_tokens()
        anchors = tokens["color"]["accent"]["anchors"]
        assert _lerp_color(11.0, anchors) == _lerp_color(10.0, anchors)

    def test_midpoint_interpolation(self):
        from sunset_predictor.renderer import _lerp_color, _load_tokens
        tokens = _load_tokens()
        anchors = tokens["color"]["accent"]["anchors"]
        low = _lerp_color(1.0, anchors)
        mid = _lerp_color(5.5, anchors)
        high = _lerp_color(10.0, anchors)
        assert mid != low
        assert mid != high


# ---------------------------------------------------------------------------
# _format_score
# ---------------------------------------------------------------------------

class TestFormatScore:
    def test_integer_score_no_decimal(self):
        from sunset_predictor.renderer import _format_score
        assert _format_score(7.0) == "7"

    def test_integer_10_no_decimal(self):
        from sunset_predictor.renderer import _format_score
        assert _format_score(10.0) == "10"

    def test_fractional_keeps_one_decimal(self):
        from sunset_predictor.renderer import _format_score
        assert _format_score(7.6) == "7.6"

    def test_integer_1_no_decimal(self):
        from sunset_predictor.renderer import _format_score
        assert _format_score(1.0) == "1"

    def test_fractional_low(self):
        from sunset_predictor.renderer import _format_score
        assert _format_score(2.3) == "2.3"


# ---------------------------------------------------------------------------
# _tracking
# ---------------------------------------------------------------------------

class TestTracking:
    def test_zero_returns_normal(self):
        from sunset_predictor.renderer import _tracking
        assert _tracking(16, 0) == "normal"

    def test_nonzero_returns_px(self):
        from sunset_predictor.renderer import _tracking
        result = _tracking(16, 5)
        assert result.endswith("px")
        assert float(result.replace("px", "")) == pytest.approx(0.8)

    def test_large_tracking(self):
        from sunset_predictor.renderer import _tracking
        result = _tracking(100, 10)
        assert result == "10.0px"
