"""Strava specific enums."""
from enum import Enum


class StravaURLs(Enum):
    """Strava specific URLs."""

    AUTH_URL = "https://www.strava.com/oauth/token"
    ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
    ACTIVITY_URL = "https://www.strava.com/api/v3/athlete/activities"
    STREAM_URL = "https://www.strava.com/api/v3/activities/{}/stream"


class StravaKeys(Enum):
    """Strava specific keys."""

    STRAVA_ACCESS_TOKEN = "strava_access_token"


class StravaStreams(Enum):
    """Strava specific steams."""
    ACTIVITY="activity"
    STREAM="heartstream"
    TIME = "time"
    HEARTRATE = "heartrate"
    DISTANCE = "distance"
    LATLNG = "latlng"
    VELOCITY_SMOOTH = "velocity_smooth"
    CADENCE = "cadence"
    WATTS = "watts"
    TEMP = "temp"
    MOVING = "moving"
    GRADE_SMOOTH = "grade_smooth"
