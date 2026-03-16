"""Shared fixtures for sunset predictor tests."""

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest


@dataclass
class MockLocation:
    name: str = "Tel Aviv"
    lat: float = 32.0853
    lon: float = 34.7818
    timezone: str = "Asia/Jerusalem"


@pytest.fixture
def location():
    return MockLocation()


@pytest.fixture
def sunset_dt():
    return datetime(2026, 3, 15, 15, 30, tzinfo=timezone.utc)


@pytest.fixture
def sun_info(sunset_dt):
    return {
        "sunset": sunset_dt,
        "azimuth": 269,
    }


def make_weather(
    cloud_pct=30,
    humidity=50,
    visibility=10000,
    condition_id=802,
    condition_desc="scattered clouds",
    cloud_layers=None,
    comfort=None,
):
    """Build a weather dict matching the format scorer.calculate_sunset_score expects."""
    w = {
        "clouds": {"all": cloud_pct},
        "main": {"humidity": humidity},
        "visibility": visibility,
        "weather": [{"id": condition_id, "description": condition_desc}],
    }
    if cloud_layers is not None:
        w["cloud_layers"] = cloud_layers
    if comfort is not None:
        w["comfort"] = comfort
    return w


def make_air_quality(pm25=10.0):
    return {"list": [{"components": {"pm2_5": pm25}}]}


def make_western_sky(near_clouds=30, near_cond_id=800, far_clouds=40):
    return {
        "near": {
            "clouds": {"all": near_clouds},
            "weather": [{"id": near_cond_id}],
        },
        "far": {
            "clouds": {"all": far_clouds},
            "weather": [{"id": 800}],
        },
    }
