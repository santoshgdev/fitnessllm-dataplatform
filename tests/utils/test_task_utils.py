import os

import pytest

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource, FitnessLLMDataStream
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.utils.task_utils import (
    get_enum_values_from_list,
    load_into_env_vars, get_schema_path,
)


def test_load_into_env_vars():
    """Test for loading options into environmental variables."""
    options = {"KEY1": "value1", "KEY2": 2, "KEY3": 3.0, "KEY4": True}
    load_into_env_vars(options)

    assert os.environ["KEY1"] == "value1"
    assert os.environ["KEY2"] == "2"
    assert os.environ["KEY3"] == "3.0"
    assert os.environ["KEY4"] == "True"


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


@pytest.mark.parametrize("data_source, data_stream, expected_output",
                         [
                                (None, None, "fitnessllm_dataplatform/schemas/metrics.json"),
                                (FitnessLLMDataSource.STRAVA, StravaStreams.ACTIVITY, "fitnessllm_dataplatform/stream/strava/schemas/activity.json"),
                                (FitnessLLMDataSource.STRAVA, StravaStreams.LATLNG, "fitnessllm_dataplatform/stream/strava/schemas/latlng.json"),
                                (FitnessLLMDataSource.STRAVA, StravaStreams.GRADE_SMOOTH, "fitnessllm_dataplatform/stream/strava/schemas/generic_stream.json"),
                         ])
def test_get_schema_path(data_source: FitnessLLMDataSource, data_stream: FitnessLLMDataStream, expected_output: str):
    """Test for loading schema from json."""
    output = get_schema_path(data_source, data_stream)
    assert output == expected_output
