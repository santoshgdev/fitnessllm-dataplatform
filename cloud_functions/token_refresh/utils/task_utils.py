"""Task utils."""

from datetime import datetime

import pytz
from fitnessllm_shared.entities.constants import TIMEZONE


def update_last_refresh() -> datetime:
    """Returns the current date and time in the configured timezone (`{TIMEZONE}`).

    Returns:
        datetime: The current localized datetime in Pacific Time.
    """
    pacific_tz = pytz.timezone(TIMEZONE)
    return datetime.now(pacific_tz)
