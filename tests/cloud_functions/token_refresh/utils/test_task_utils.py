from datetime import datetime

import pytz
from fitnessllm_shared.entities.constants import TIMEZONE
from freezegun import freeze_time

from cloud_functions.token_refresh.utils.task_utils import update_last_refresh


def test_update_last_refresh_pacific():
    utc_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
    pacific = pytz.timezone(TIMEZONE)

    expected = utc_time.astimezone(pacific)

    with freeze_time(utc_time):
        actual = update_last_refresh()
        assert actual == expected
