import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Location:
    name: str
    lat: float
    lon: float
    timezone: str

    @property
    def tz(self):
        return ZoneInfo(self.timezone)


TEL_AVIV = Location(
    name="Tel Aviv",
    lat=32.0853,
    lon=34.7818,
    timezone="Asia/Jerusalem",
)

DEFAULT_LOCATION = TEL_AVIV

API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
