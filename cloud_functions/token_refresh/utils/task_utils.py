"""Task utils."""
from datetime import datetime

import pytz


def update_last_refresh() -> datetime:
    """Return the current time."""
    pacific_tz = pytz.timezone("America/Los_Angeles")
    return datetime.now(pacific_tz)
