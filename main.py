import sys

from sunset_predictor.config import DEFAULT_LOCATION
from sunset_predictor.fetcher import OpenMeteoFetcher
from sunset_predictor.formatter import print_prediction
from sunset_predictor.scorer import calculate_sunset_score, get_verdict
from sunset_predictor.sun import get_sunset_info, get_western_sky_points


def main():
    location = DEFAULT_LOCATION

    sun_info = get_sunset_info(
        location.lat, location.lon, location.timezone, location.name
    )

    western_points = get_western_sky_points(
        location.lat, location.lon, sun_info["azimuth"]
    )

    fetcher = OpenMeteoFetcher()

    try:
        weather = fetcher.get_weather_at_sunset(
            location.lat, location.lon, sun_info["sunset"]
        )
        air_quality = fetcher.get_air_quality(location.lat, location.lon)
        western_sky = fetcher.get_western_sky_weather(
            western_points, sun_info["sunset"]
        )
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    result = calculate_sunset_score(weather, air_quality, western_sky)
    result["raw"]["comfort"] = weather.get("comfort")
    verdict = get_verdict(result["overall"])

    print_prediction(location, sun_info, result, verdict)


if __name__ == "__main__":
    main()
