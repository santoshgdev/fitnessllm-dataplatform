"""Module for used task utilities."""
import json
import os
from datetime import datetime
from enum import Enum

from google.cloud import bigquery

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource, FitnessLLMDataStream


def load_into_env_vars(options: dict):
    """Loads a given dict with options into environmental variables.

    Args:
        options: dict with options to load
    """
    for key, value in options.items():
        if type(value) in [str, int, float, bool]:
            os.environ[key] = str(value)


def get_enum_values_from_list(enum: list[Enum]):
    return [member.value for member in enum]


def dataclass_convertor(data):
    if isinstance(data, Enum):
        return data.value
    if isinstance(data, datetime):
        return data.isoformat()
    return data


def get_schema_path(data_source: FitnessLLMDataSource | None, data_stream: FitnessLLMDataStream | None) -> str:
    if data_source and data_stream:
        return f"fitnessllm_dataplatform/stream/{data_source.value.lower()}/schemas/{data_stream.value.lower()}.json"
    return "fitnessllm_dataplatform/schemas/metrics.json"


def load_schema_from_json(data_source: FitnessLLMDataSource, data_stream: FitnessLLMDataStream) -> list[bigquery.SchemaField]:
    with open(get_schema_path(data_source, data_stream), 'r') as f:
        schema_json = json.load(f)

    return [
        bigquery.SchemaField(
            name=field['name'],
            field_type=field['type'],
            mode=field.get('mode', 'NULLABLE'),
            description=field.get('description', '')
        ) for field in schema_json
    ]