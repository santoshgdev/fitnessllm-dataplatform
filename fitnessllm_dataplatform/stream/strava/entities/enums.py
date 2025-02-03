"""Strava specific enums."""
from enum import Enum

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataStream


class StravaURLs(Enum):
    """Strava specific URLs."""

    AUTH_URL = "https://www.strava.com/oauth/token"
    ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
    ACTIVITY_URL = "https://www.strava.com/api/v3/athlete/activities"
    STREAM_URL = "https://www.strava.com/api/v3/activities/{}/stream"


class StravaKeys(Enum):
    """Strava specific keys."""

    STRAVA_ACCESS_TOKEN = "strava_access_token"


class StravaStreams(FitnessLLMDataStream):
    ACTIVITY = "activity"
    ATHLETE_SUMMARY = "athlete_summary"
    TIME = "time"
    DISTANCE = "distance"
    LATLNG = "latlng"
    ALTITUDE = "altitude"
    VELOCITY_SMOOTH = "velocity_smooth"
    HEARTRATE = "heartrate"
    CADENCE = "cadence"
    WATTS = "watts"
    TEMP = "temp"
    MOVING = "moving"
    GRADE_SMOOTH = "grade_smooth"

    @classmethod
    def filter_streams(cls, include=None, exclude=None) -> list[Enum]:
        if include:
            return [member for member in cls if member.name in include]
        if exclude:
            return [member for member in cls if member.name not in exclude]
