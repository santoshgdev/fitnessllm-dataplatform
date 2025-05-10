"""Task utils."""
from datetime import datetime

import pytz


def update_last_refresh() -> datetime:
    """
    Returns the current date and time in the America/Los_Angeles timezone.
    
    Returns:
        datetime: The current localized datetime in Pacific Time.
    """
    pacific_tz = pytz.timezone("America/Los_Angeles")
    return datetime.now(pacific_tz)
