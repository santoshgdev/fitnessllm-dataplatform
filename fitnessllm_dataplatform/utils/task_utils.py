"""Module for used task utilities."""
import json
import os
from datetime import datetime
from enum import Enum

from google.cloud import bigquery

from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
)
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams


def load_into_env_vars(options: dict):
    """Loads a given dict with options into environmental variables.

    Args:
        options: dict with options to load
    """
    for key, value in options.items():
        if type(value) in [str, int, float, bool]:
            os.environ[key] = str(value)


def get_enum_values_from_list(enum: list[Enum]):
    """Returns a list of values from an Enum list."""
    if not all(isinstance(item, Enum) for item in enum):
        raise TypeError("All items in the list must be Enum instances")
    return [member.value for member in enum]


def dataclass_convertor(data):
    """Converts attributes."""
    if isinstance(data, Enum):
        return data.value
    if isinstance(data, datetime):
        return data.isoformat()
    return data


def get_schema_path(
    data_source: FitnessLLMDataSource | None, data_stream: FitnessLLMDataStream | None
) -> str:
    """Returns the path to the schema file."""
    if data_source and data_stream:
        schema_name = (
            "generic_stream"
            if data_stream
            in StravaStreams.filter_streams(
                exclude=["ACTIVITY", "ATHLETE_SUMMARY", "LATLNG"]
            )
            else data_stream.value.lower()
        )
        return f"fitnessllm_dataplatform/stream/{data_source.value.lower()}/schemas/{schema_name}.json"
    return "fitnessllm_dataplatform/schemas/metrics.json"


def load_schema_from_json(
    data_source: FitnessLLMDataSource, data_stream: FitnessLLMDataStream
) -> list[bigquery.SchemaField]:
    """Loads schema from JSON file."""
    schema_path = get_schema_path(data_source, data_stream)
    try:
        with open(schema_path) as f:
            schema_json = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in schema file {schema_path}: {e}")

    required_fields = {"name", "type"}
    for field in schema_json:
        if not isinstance(field, dict):
            raise ValueError(f"Invalid field in schema: {field}")
        missing_fields = required_fields - set(field.keys())
        if missing_fields:
            raise ValueError(
                f"Missing required fields {missing_fields} in field: {field}"
            )

    return [
        bigquery.SchemaField(
            name=field["name"],
            field_type=field["type"],
            mode=field.get("mode", "NULLABLE"),
            description=field.get("description", ""),
        )
        for field in schema_json
    ]
