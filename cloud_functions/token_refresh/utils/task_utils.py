from datetime import datetime

import pytz


def update_last_refresh():
    # Create a timestamp for UTC-7 (Pacific Time)
    pacific_tz = pytz.timezone('America/Los_Angeles')
    timestamp = datetime.now(pacific_tz)

    return timestamp