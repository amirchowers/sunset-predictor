"""Tests for sunset_predictor.scorer — threshold functions, weighted scoring, verdicts."""

import pytest

from sunset_predictor.scorer import (
    _score_air_quality,
    _score_cloud_cover,
    _score_cloud_high,
    _score_cloud_low_mid,
    _score_humidity,
    _score_visibility,
    _score_weather_condition,
    _score_western_far,
    _score_western_near,
    calculate_sunset_score,
    get_verdict,
    WEIGHTS,
    WEIGHTS_LEGACY,
)
from tests.conftest import make_air_quality, make_weather, make_western_sky


# ---------------------------------------------------------------------------
# _score_cloud_cover (legacy fallback)
# ---------------------------------------------------------------------------

class TestScoreCloudCover:
    @pytest.mark.parametrize("pct, expected", [
        (0, 3.0),
        (5, 3.0),
        (10, 5.5),
        (20, 5.5),
        (25, 9.0),
        (40, 9.0),
        (50, 10.0),
        (60, 10.0),
        (70, 6.0),
        (75, 6.0),
        (80, 3.0),
        (90, 3.0),
        (95, 1.0),
        (100, 1.0),
    ])
    def test_thresholds(self, pct, expected):
        assert _score_cloud_cover(pct) == expected


# ---------------------------------------------------------------------------
# _score_cloud_high
# ---------------------------------------------------------------------------

class TestScoreCloudHigh:
    @pytest.mark.parametrize("pct, expected", [
        (0, 4.0),
        (5, 4.0),
        (6, 7.0),
        (20, 7.0),
        (21, 10.0),
        (50, 10.0),
        (51, 8.0),
        (70, 8.0),
        (71, 5.0),
        (85, 5.0),
        (86, 3.0),
        (100, 3.0),
    ])
    def test_thresholds(self, pct, expected):
        assert _score_cloud_high(pct) == expected


# ---------------------------------------------------------------------------
# _score_cloud_low_mid
# ---------------------------------------------------------------------------

class TestScoreCloudLowMid:
    def test_high_low_clouds_blocks(self):
        assert _score_cloud_low_mid(80, 0) == 1.0

    def test_moderate_low_clouds_dims(self):
        assert _score_cloud_low_mid(60, 0) == 3.0

    def test_combined_impact_very_high(self):
        # low=40, mid=50 -> impact = 40*1.5 + 50 = 110 -> >80 -> 3.0
        assert _score_cloud_low_mid(40, 50) == 3.0

    def test_combined_impact_high(self):
        # low=30, mid=30 -> impact = 30*1.5 + 30 = 75 -> >50 -> 5.0
        assert _score_cloud_low_mid(30, 30) == 5.0

    def test_combined_impact_moderate(self):
        # low=10, mid=15 -> impact = 10*1.5 + 15 = 30 -> >20 -> 8.0
        assert _score_cloud_low_mid(10, 15) == 8.0

    def test_clear_skies(self):
        # low=0, mid=0 -> impact = 0 -> <=20 -> 9.0
        assert _score_cloud_low_mid(0, 0) == 9.0

    def test_extreme_overcast(self):
        # low=100, mid=100 -> low > 70 -> 1.0
        assert _score_cloud_low_mid(100, 100) == 1.0

    def test_combined_impact_over_120(self):
        # low=50 is NOT > 50, so falls through to impact calc:
        # impact = 50*1.5 + 80 = 155 -> >120 -> 1.0
        assert _score_cloud_low_mid(50, 80) == 1.0
        # low=45, mid=60 -> impact = 45*1.5 + 60 = 127.5 -> >120 -> 1.0
        assert _score_cloud_low_mid(45, 60) == 1.0


# ---------------------------------------------------------------------------
# _score_humidity
# ---------------------------------------------------------------------------

class TestScoreHumidity:
    @pytest.mark.parametrize("pct, expected", [
        (0, 10.0),
        (30, 10.0),
        (31, 8.0),
        (50, 8.0),
        (51, 6.0),
        (65, 6.0),
        (66, 3.0),
        (80, 3.0),
        (81, 1.0),
        (100, 1.0),
    ])
    def test_thresholds(self, pct, expected):
        assert _score_humidity(pct) == expected


# ---------------------------------------------------------------------------
# _score_visibility
# ---------------------------------------------------------------------------

class TestScoreVisibility:
    @pytest.mark.parametrize("meters, expected", [
        (50000, 10.0),
        (10000, 10.0),
        (9999, 8.0),
        (7000, 8.0),
        (6999, 5.0),
        (4000, 5.0),
        (3999, 3.0),
        (2000, 3.0),
        (1999, 1.0),
        (0, 1.0),
    ])
    def test_thresholds(self, meters, expected):
        assert _score_visibility(meters) == expected


# ---------------------------------------------------------------------------
# _score_air_quality
# ---------------------------------------------------------------------------

class TestScoreAirQuality:
    @pytest.mark.parametrize("pm25, expected", [
        (0, 5.0),
        (5, 5.0),
        (6, 7.0),
        (15, 7.0),
        (16, 10.0),
        (35, 10.0),
        (36, 6.0),
        (55, 6.0),
        (56, 3.0),
        (75, 3.0),
        (76, 1.0),
        (200, 1.0),
    ])
    def test_thresholds(self, pm25, expected):
        assert _score_air_quality(pm25) == expected


# ---------------------------------------------------------------------------
# _score_western_near
# ---------------------------------------------------------------------------

class TestScoreWesternNear:
    def test_precipitation_always_kills(self):
        for cond_id in [200, 300, 500, 600, 699]:
            assert _score_western_near(30, cond_id) == 1.0

    def test_heavy_overcast(self):
        assert _score_western_near(95, 800) == 1.0

    @pytest.mark.parametrize("pct, expected", [
        (91, 1.0),    # > 90
        (90, 3.0),    # NOT > 90, falls to > 80
        (85, 3.0),
        (81, 3.0),
        (80, 5.0),    # NOT > 80, falls to > 70
        (75, 5.0),
        (71, 5.0),
        (70, 8.0),    # NOT > 70, falls to > 50
        (55, 8.0),
        (51, 8.0),
        (50, 10.0),   # NOT > 50, falls to > 25
        (30, 10.0),
        (26, 10.0),
        (25, 7.0),    # NOT > 25, falls to > 10
        (15, 7.0),
        (11, 7.0),
        (10, 5.0),    # NOT > 10, falls to default
        (5, 5.0),
        (0, 5.0),
    ])
    def test_cloud_thresholds_clear_weather(self, pct, expected):
        assert _score_western_near(pct, 800) == expected


# ---------------------------------------------------------------------------
# _score_western_far
# ---------------------------------------------------------------------------

class TestScoreWesternFar:
    @pytest.mark.parametrize("pct, expected", [
        (0, 4.0),
        (5, 4.0),
        (6, 6.0),
        (20, 6.0),
        (21, 10.0),
        (50, 10.0),
        (51, 8.0),
        (70, 8.0),
        (71, 5.0),
        (85, 5.0),
        (86, 2.0),
        (100, 2.0),
    ])
    def test_thresholds(self, pct, expected):
        assert _score_western_far(pct) == expected


# ---------------------------------------------------------------------------
# _score_weather_condition
# ---------------------------------------------------------------------------

class TestScoreWeatherCondition:
    @pytest.mark.parametrize("cond_id, expected", [
        (200, 1.0),    # thunderstorm
        (299, 1.0),
        (500, 2.0),    # rain
        (599, 2.0),
        (600, 1.0),    # snow
        (699, 1.0),
        (300, 3.0),    # drizzle
        (399, 3.0),
        (700, 3.0),    # atmosphere (fog/mist)
        (799, 3.0),
        (800, 6.0),    # clear
        (801, 8.0),    # few clouds
        (802, 10.0),   # scattered clouds (ideal)
        (803, 8.0),    # broken clouds
    ])
    def test_condition_scores(self, cond_id, expected):
        assert _score_weather_condition(cond_id) == expected

    def test_overcast_with_clear_west(self):
        assert _score_weather_condition(804, western_near_clouds=30) == 6.0

    def test_overcast_with_partial_west(self):
        assert _score_weather_condition(804, western_near_clouds=60) == 5.0

    def test_overcast_with_blocked_west(self):
        assert _score_weather_condition(804, western_near_clouds=80) == 2.0

    def test_overcast_no_western_data(self):
        assert _score_weather_condition(804) == 2.0

    def test_unknown_condition_fallback(self):
        assert _score_weather_condition(900) == 5.0


# ---------------------------------------------------------------------------
# calculate_sunset_score — 8-factor path (with cloud_layers)
# ---------------------------------------------------------------------------

class TestCalculateSunsetScore8Factor:
    def test_known_inputs(self):
        weather = make_weather(
            cloud_pct=30,
            humidity=50,
            visibility=10000,
            condition_id=802,
            cloud_layers={"high": 30, "mid": 10, "low": 5},
        )
        aq = make_air_quality(pm25=20.0)
        ws = make_western_sky(near_clouds=35, far_clouds=40)

        result = calculate_sunset_score(weather, aq, ws)

        assert result["has_cloud_layers"] is True
        assert "cloud_high" in result["scores"]
        assert "cloud_low_mid" in result["scores"]
        assert "cloud_cover" not in result["scores"]

        expected_scores = {
            "cloud_high": _score_cloud_high(30),        # 10.0
            "cloud_low_mid": _score_cloud_low_mid(5, 10),  # 8.0 (impact=17.5)
            "western_near": _score_western_near(35, 800),  # 10.0
            "western_far": _score_western_far(40),        # 10.0
            "humidity": _score_humidity(50),               # 8.0
            "visibility": _score_visibility(10000),        # 10.0
            "air_quality": _score_air_quality(20.0),       # 10.0
            "weather_condition": _score_weather_condition(802, 35),  # 10.0
        }
        expected_overall = round(
            sum(expected_scores[k] * WEIGHTS[k] for k in WEIGHTS), 1
        )

        assert result["scores"] == expected_scores
        assert result["overall"] == expected_overall

    def test_raw_values_include_cloud_layers(self):
        weather = make_weather(
            cloud_pct=30,
            humidity=50,
            visibility=10000,
            condition_id=802,
            cloud_layers={"high": 30, "mid": 10, "low": 5},
        )
        result = calculate_sunset_score(
            weather, make_air_quality(), make_western_sky()
        )
        assert result["raw"]["cloud_high_pct"] == 30
        assert result["raw"]["cloud_mid_pct"] == 10
        assert result["raw"]["cloud_low_pct"] == 5


# ---------------------------------------------------------------------------
# calculate_sunset_score — 7-factor path (legacy, no cloud_layers)
# ---------------------------------------------------------------------------

class TestCalculateSunsetScoreLegacy:
    def test_known_inputs(self):
        weather = make_weather(
            cloud_pct=40,
            humidity=60,
            visibility=8000,
            condition_id=801,
        )
        aq = make_air_quality(pm25=12.0)
        ws = make_western_sky(near_clouds=25, far_clouds=30)

        result = calculate_sunset_score(weather, aq, ws)

        assert result["has_cloud_layers"] is False
        assert "cloud_cover" in result["scores"]
        assert "cloud_high" not in result["scores"]

        expected_scores = {
            "cloud_cover": _score_cloud_cover(40),
            "western_near": _score_western_near(25, 800),
            "western_far": _score_western_far(30),
            "humidity": _score_humidity(60),
            "visibility": _score_visibility(8000),
            "air_quality": _score_air_quality(12.0),
            "weather_condition": _score_weather_condition(801, 25),
        }
        expected_overall = round(
            sum(expected_scores[k] * WEIGHTS_LEGACY[k] for k in WEIGHTS_LEGACY), 1
        )

        assert result["scores"] == expected_scores
        assert result["overall"] == expected_overall

    def test_raw_values_no_cloud_layers(self):
        weather = make_weather(cloud_pct=40, humidity=60, visibility=8000)
        result = calculate_sunset_score(
            weather, make_air_quality(), make_western_sky()
        )
        assert "cloud_high_pct" not in result["raw"]
        assert result["raw"]["cloud_cover_pct"] == 40


# ---------------------------------------------------------------------------
# get_verdict
# ---------------------------------------------------------------------------

class TestGetVerdict:
    @pytest.mark.parametrize("score, expected_verdict", [
        (10.0, "Tell your friends — rare show"),
        (8.0, "Tell your friends — rare show"),
        (7.9, "Worth making plans for"),
        (6.5, "Worth making plans for"),
        (6.4, "Watchable — sun meets the sea"),
        (5.0, "Watchable — sun meets the sea"),
        (4.9, "Probably blocked or dull"),
        (3.5, "Probably blocked or dull"),
        (3.4, "Skip it"),
        (0.0, "Skip it"),
    ])
    def test_verdict_thresholds(self, score, expected_verdict):
        assert get_verdict(score) == expected_verdict
