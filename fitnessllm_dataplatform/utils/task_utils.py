"""Module for used task utilities."""
import base64
import json
import os
from datetime import datetime
from enum import Enum
from json.decoder import JSONDecodeError

from beartype import beartype
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from google.cloud import bigquery

from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
)
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.utils.logging_utils import logger


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
        return f"fitnessllm_dataplatform/stream/{data_source.value.lower()}/schemas/bronze/json/{schema_name}.json"
    return "fitnessllm_dataplatform/schemas/metrics.json"


def load_schema_from_json(
    data_source: FitnessLLMDataSource | None, data_stream: FitnessLLMDataStream | None
) -> list[bigquery.SchemaField]:
    """Loads schema from JSON file."""
    schema_path = get_schema_path(data_source, data_stream)
    try:
        with open(schema_path) as f:
            schema_json = json.load(f)
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        raise
    except JSONDecodeError:
        logger.error(f"Invalid JSON in schema file: {schema_path}")
        raise

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


@beartype
def decrypt_token(encrypted_token: str, key: str) -> str:
    """Decrypt a token that was encrypted using AES-256-CBC in JavaScript.

    Args:
        encrypted_token (str): The encrypted token in format "iv:encrypted"
        key (str or bytes): The encryption key

    Returns:
        str: The decrypted token
    """
    # Split the IV and encrypted data
    parts = encrypted_token.split(":")
    if len(parts) != 2:
        raise ValueError("Invalid encrypted token format")

    # Decode IV and encrypted data from base64
    iv = base64.b64decode(parts[0])
    encrypted_data = base64.b64decode(parts[1])

    # Prepare the key (ensure its bytes)
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key

    # For AES-256-CBC, the key must be 32 bytes
    if len(key_bytes) != 32:
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b"\0")  # Pad with zeros
        else:
            key_bytes = key_bytes[:32]  # Truncate

    # Create decipher
    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # Decrypt
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    # Remove padding (PKCS#7 padding is used by default in AES-CBC)
    padding_length = decrypted_data[-1]
    if 0 < padding_length <= 16:  # Sanity check for padding
        decrypted_data = decrypted_data[:-padding_length]

    # Return as string
    return decrypted_data.decode("utf-8")
