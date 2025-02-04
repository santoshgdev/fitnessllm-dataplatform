import os

from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.utils.task_utils import (
    get_enum_values_from_list,
    load_into_env_vars,
)


def test_load_into_env_vars():
    """Test for loading options into environmental variables."""
    options = {"key1": "value1", "key2": 2, "key3": 3.0, "key4": True}
    load_into_env_vars(options)

    assert os.environ["key1"] == "value1"
    assert os.environ["key2"] == "2"
    assert os.environ["key3"] == "3.0"
    assert os.environ["key4"] == "True"


def test_get_enum_values_from_list():
    """Test for getting values from enum list."""
    enum_list = [
        StravaStreams.ACTIVITY,
        StravaStreams.ATHLETE_SUMMARY,
        StravaStreams.GRADE_SMOOTH,
    ]
    assert get_enum_values_from_list(enum_list) == [
        "activity",
        "athlete_summary",
        "grade_smooth",
    ]
