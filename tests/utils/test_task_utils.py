import os
from datetime import datetime
from json.decoder import JSONDecodeError
from unittest.mock import patch

import pytest
from google.cloud.bigquery import SchemaField

from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
)
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.utils.task_utils import (
    dataclass_convertor,
    get_enum_values_from_list,
    get_schema_path,
    load_into_env_vars,
    load_schema_from_json,
)


@pytest.mark.parametrize(
    "options",
    [({"KEY1": "value1", "KEY2": 2, "KEY3": 3.0, "KEY4": True}), ({"KEY1": []})],
)
def test_load_into_env_vars(options):
    """Test for loading options into environmental variables."""
    load_into_env_vars(options)

    for key, value in options.items():
        if type(value) in [str, int, float, bool]:
            assert os.environ.get(key) == str(value)
            del os.environ[key]
        else:
            assert os.environ.get(key) is None


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


def test_get_enum_values_from_list_error():
    enum_list = [
        StravaStreams.ACTIVITY,
        StravaStreams.ATHLETE_SUMMARY,
        StravaStreams.GRADE_SMOOTH,
        "test",
    ]
    with pytest.raises(TypeError):
        get_enum_values_from_list(enum_list)


def test_dataclass_convertor():
    """Test for converting attributes."""
    now = datetime.now()
    assert dataclass_convertor(StravaStreams.ACTIVITY) == "activity"
    assert dataclass_convertor(1) == 1
    assert dataclass_convertor(1.0) == 1.0
    assert dataclass_convertor(True)
    assert dataclass_convertor("test") == "test"
    assert dataclass_convertor(now) == now.isoformat()


@pytest.mark.parametrize(
    "data_source, data_stream, expected_output",
    [
        (None, None, "fitnessllm_dataplatform/schemas/metrics.json"),
        (
            FitnessLLMDataSource.STRAVA,
            StravaStreams.ACTIVITY,
            "fitnessllm_dataplatform/stream/strava/schemas/activity.json",
        ),
        (
            FitnessLLMDataSource.STRAVA,
            StravaStreams.LATLNG,
            "fitnessllm_dataplatform/stream/strava/schemas/latlng.json",
        ),
        (
            FitnessLLMDataSource.STRAVA,
            StravaStreams.GRADE_SMOOTH,
            "fitnessllm_dataplatform/stream/strava/schemas/generic_stream.json",
        ),
    ],
)
def test_get_schema_path(
    data_source: FitnessLLMDataSource,
    data_stream: FitnessLLMDataStream,
    expected_output: str,
):
    """Test for loading schema from json."""
    output = get_schema_path(data_source, data_stream)
    assert output == expected_output


def test_load_schema_from_json():
    """Test for loading schema from json with error."""
    expected_output = [
        SchemaField("athlete_id", "STRING", "REQUIRED", None, "athlete_id", (), None),
        SchemaField("activity_id", "STRING", "REQUIRED", None, "activity_id", (), None),
        SchemaField(
            "data_source",
            "STRING",
            "REQUIRED",
            None,
            "Datasource (e.g. Strava)",
            (),
            None,
        ),
        SchemaField("data_stream", "STRING", "REQUIRED", None, "Stream type", (), None),
        SchemaField(
            "record_count", "INTEGER", "REQUIRED", None, "Number of records", (), None
        ),
        SchemaField("status", "STRING", "REQUIRED", None, "Record status", (), None),
        SchemaField(
            "bq_insert_timestamp",
            "TIMESTAMP",
            "REQUIRED",
            None,
            "Number of records",
            (),
            None,
        ),
    ]
    output = load_schema_from_json(data_source=None, data_stream=None)
    assert output == expected_output


@patch("fitnessllm_dataplatform.utils.task_utils.get_schema_path")
@pytest.mark.parametrize(
    "input, message, expected_output",
    [
        (
            "fitnessllm_dataplatform/schemas/metrics1.json",
            "Schema file not found: fitnessllm_dataplatform/schemas/metrics1.json",
            FileNotFoundError,
        ),
        (
            "tests/data/schemas/bad_json.json",
            "Invalid JSON in schema file: tests/data/schemas/bad_json.json",
            JSONDecodeError,
        ),
        (
            "tests/data/schemas/non_dict_json.json",
            "Invalid field in schema: bad_field",
            ValueError,
        ),
        (
            "tests/data/schemas/bad_field.json",
            "Missing required fields {'type'} in field: {'name': 'index', 'mode': 'NULLABLE'}",
            ValueError,
        ),
    ],
)
def test_load_schema_from_json_error(
    mock_get_schema_path,
    caplog,
    input,
    message,
    expected_output,
):
    mock_get_schema_path.return_value = input

    with pytest.raises(expected_output) as exc:
        load_schema_from_json(
            data_source=FitnessLLMDataSource.STRAVA, data_stream=StravaStreams.ACTIVITY
        )

    if exc.type is ValueError:
        assert message in exc.value.args
    else:
        assert message in caplog.text
