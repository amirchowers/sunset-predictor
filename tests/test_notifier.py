"""Tests for sunset_predictor.notifier — message formatting and comfort warnings."""

import pytest

from sunset_predictor.notifier import _comfort_warnings, _score_bar, format_message
from tests.conftest import MockLocation


# ---------------------------------------------------------------------------
# _score_bar
# ---------------------------------------------------------------------------

class TestScoreBar:
    def test_zero(self):
        bar = _score_bar(0, width=10)
        assert bar == "\u26aa" * 10

    def test_ten(self):
        bar = _score_bar(10, width=10)
        assert bar == "\U0001f7e0" * 10

    def test_five(self):
        bar = _score_bar(5, width=10)
        assert bar == "\U0001f7e0" * 5 + "\u26aa" * 5

    def test_custom_width(self):
        bar = _score_bar(5, width=20)
        assert bar == "\U0001f7e0" * 10 + "\u26aa" * 10

    def test_rounding(self):
        bar = _score_bar(7.5, width=10)
        filled = int(round(7.5 / 10 * 10))
        assert bar == "\U0001f7e0" * filled + "\u26aa" * (10 - filled)


# ---------------------------------------------------------------------------
# _comfort_warnings
# ---------------------------------------------------------------------------

class TestComfortWarnings:
    def test_none_comfort(self):
        assert _comfort_warnings(None) == []

    def test_no_warnings_mild(self):
        comfort = {"wind_kmh": 10, "wind_gusts_kmh": 15, "temp_c": 22, "feels_like_c": 22}
        assert _comfort_warnings(comfort) == []

    def test_very_windy(self):
        comfort = {"wind_kmh": 45, "wind_gusts_kmh": 60, "temp_c": 20, "feels_like_c": 20}
        warnings = _comfort_warnings(comfort)
        assert len(warnings) == 1
        assert "Very windy" in warnings[0]
        assert "45" in warnings[0]

    def test_windy(self):
        comfort = {"wind_kmh": 30, "wind_gusts_kmh": 40, "temp_c": 20, "feels_like_c": 20}
        warnings = _comfort_warnings(comfort)
        assert len(warnings) == 1
        assert "Windy" in warnings[0]
        assert "Very" not in warnings[0]

    def test_cold(self):
        comfort = {"wind_kmh": 5, "wind_gusts_kmh": 5, "temp_c": 5, "feels_like_c": 3}
        warnings = _comfort_warnings(comfort)
        assert len(warnings) == 1
        assert "Cold" in warnings[0]

    def test_cool(self):
        comfort = {"wind_kmh": 5, "wind_gusts_kmh": 5, "temp_c": 14, "feels_like_c": 12}
        warnings = _comfort_warnings(comfort)
        assert len(warnings) == 1
        assert "Cool" in warnings[0]

    def test_windy_and_cold(self):
        comfort = {"wind_kmh": 30, "wind_gusts_kmh": 40, "temp_c": 5, "feels_like_c": 0}
        warnings = _comfort_warnings(comfort)
        assert len(warnings) == 2

    def test_wind_threshold_boundary_25(self):
        comfort = {"wind_kmh": 25, "wind_gusts_kmh": 30, "temp_c": 20, "feels_like_c": 20}
        warnings = _comfort_warnings(comfort)
        assert len(warnings) == 1
        assert "Windy" in warnings[0]

    def test_wind_below_threshold(self):
        comfort = {"wind_kmh": 24, "wind_gusts_kmh": 30, "temp_c": 20, "feels_like_c": 20}
        assert _comfort_warnings(comfort) == []

    def test_feels_like_boundary_8(self):
        comfort = {"wind_kmh": 5, "wind_gusts_kmh": 5, "temp_c": 10, "feels_like_c": 8}
        warnings = _comfort_warnings(comfort)
        assert len(warnings) == 1
        assert "Cool" in warnings[0]

    def test_feels_like_boundary_15(self):
        comfort = {"wind_kmh": 5, "wind_gusts_kmh": 5, "temp_c": 16, "feels_like_c": 15}
        assert _comfort_warnings(comfort) == []


# ---------------------------------------------------------------------------
# format_message
# ---------------------------------------------------------------------------

class TestFormatMessage:
    @pytest.fixture
    def sample_result_8factor(self):
        return {
            "overall": 7.6,
            "scores": {
                "cloud_high": 4.0,
                "cloud_low_mid": 5.0,
                "western_near": 10.0,
                "western_far": 10.0,
                "humidity": 3.0,
                "visibility": 10.0,
                "air_quality": 10.0,
                "weather_condition": 8.0,
            },
            "raw": {
                "cloud_high_pct": 0,
                "cloud_mid_pct": 0,
                "cloud_low_pct": 40,
                "cloud_cover_pct": 30,
                "humidity_pct": 68,
                "visibility_km": 36.7,
                "pm2_5": 17.6,
                "condition": "mainly clear",
                "western_near_clouds_pct": 43,
                "western_far_clouds_pct": 21,
                "comfort": None,
            },
            "has_cloud_layers": True,
        }

    @pytest.fixture
    def sample_result_legacy(self):
        return {
            "overall": 6.0,
            "scores": {
                "cloud_cover": 9.0,
                "western_near": 8.0,
                "western_far": 6.0,
                "humidity": 6.0,
                "visibility": 10.0,
                "air_quality": 7.0,
                "weather_condition": 8.0,
            },
            "raw": {
                "cloud_cover_pct": 30,
                "humidity_pct": 55,
                "visibility_km": 12.0,
                "pm2_5": 8.0,
                "condition": "few clouds",
                "western_near_clouds_pct": 50,
                "western_far_clouds_pct": 15,
                "comfort": None,
            },
            "has_cloud_layers": False,
        }

    def test_contains_location_name(self, sample_result_8factor, sun_info, location):
        msg = format_message(sample_result_8factor, "Worth making plans for", sun_info, location)
        assert "Tel Aviv" in msg

    def test_contains_score_and_verdict(self, sample_result_8factor, sun_info, location):
        msg = format_message(sample_result_8factor, "Worth making plans for", sun_info, location)
        assert "7.6/10" in msg
        assert "Worth making plans for" in msg

    def test_contains_sunset_time(self, sample_result_8factor, sun_info, location):
        msg = format_message(sample_result_8factor, "Worth making plans for", sun_info, location)
        assert "17:30" in msg

    def test_8factor_shows_high_and_low_mid(self, sample_result_8factor, sun_info, location):
        msg = format_message(sample_result_8factor, "Worth making plans for", sun_info, location)
        assert "High clouds" in msg
        assert "Low/mid" in msg

    def test_legacy_shows_clouds(self, sample_result_legacy, sun_info, location):
        msg = format_message(sample_result_legacy, "Watchable", sun_info, location)
        assert "Clouds:" in msg
        assert "High clouds" not in msg

    def test_contains_all_factors(self, sample_result_8factor, sun_info, location):
        msg = format_message(sample_result_8factor, "Worth making plans for", sun_info, location)
        assert "West (near)" in msg
        assert "West (far)" in msg
        assert "Humidity" in msg
        assert "Visibility" in msg
        assert "Air quality" in msg

    def test_comfort_warnings_included(self, sample_result_8factor, sun_info, location):
        sample_result_8factor["raw"]["comfort"] = {
            "wind_kmh": 35, "wind_gusts_kmh": 50,
            "temp_c": 20, "feels_like_c": 20,
        }
        msg = format_message(sample_result_8factor, "Worth making plans for", sun_info, location)
        assert "Windy" in msg

    def test_no_comfort_no_warnings(self, sample_result_8factor, sun_info, location):
        sample_result_8factor["raw"]["comfort"] = None
        msg = format_message(sample_result_8factor, "Test", sun_info, location)
        assert "Windy" not in msg
        assert "Cold" not in msg

    def test_tip_included_when_provided(self, sample_result_8factor, sun_info, location):
        msg = format_message(
            sample_result_8factor, "Worth making plans for", sun_info, location,
            tip="Grab an Aperol Spritz and head to the Jaffa port."
        )
        assert "Aperol Spritz" in msg
        assert "Jaffa" in msg

    def test_tip_absent_when_none(self, sample_result_8factor, sun_info, location):
        msg = format_message(
            sample_result_8factor, "Worth making plans for", sun_info, location,
            tip=None
        )
        assert "\U0001f4a1" not in msg
