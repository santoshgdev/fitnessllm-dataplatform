"""Utils to interact with cloud resources."""

import json
import traceback
from os import environ

from cloudpathlib import CloudPath
from fitnessllm_shared.logger_utils import structured_logger
from google.cloud import secretmanager


def create_resource_path(project_id: str, service: str, name: str) -> str:
    """Simple builder for resource paths."""
    return f"projects/{project_id}/{service}/{name}/versions/latest"


def get_secret(name: str) -> dict:
    """Retrieve secret from secret manager."""
    if "PROJECT_ID" not in environ:
        raise KeyError("PROJECT_ID environment variable is not set")
    structured_logger.debug("Initializing secret manager")
    client = secretmanager.SecretManagerServiceClient()
    structured_logger.debug(f"Getting secret for {name}")
    try:
        response = client.access_secret_version(
            request={
                "name": create_resource_path(environ["PROJECT_ID"], "secrets", name)
            }
        )
        structured_logger.debug(f"Secret manager response: {response}")
        secret_payload = response.payload.data.decode("UTF-8")
        return json.loads(secret_payload)
    except Exception as e:
        structured_logger.error(
            message=f"Failed to retrieve or decode secret {name}",
            exception=str(e),
            traceback=traceback.format_exc(),
        )
        raise


def write_json_to_storage(path: CloudPath, data: dict | list) -> None:
    """Write dict as a json to storage.

    Args:
        path (CloudPath): CloudPath object.
        data (dict | list): Data to be written.

    Raises:
        Exception: If writing to storage fails.
    """
    try:
        with path.open("w") as f:
            json.dump(data, f)
    except Exception as e:
        structured_logger.error(
            message="Failed to write data to storage",
            exception=str(e),
        )
        raise e


def wrapped_write_json_to_storage(
    path: CloudPath,
    data: dict | list,
    uid: str,
    data_source: str,
) -> None:
    """Write JSON data to storage with structured error logging.

    This function wraps the write_json_to_storage function with structured logging
    for better error tracking and debugging.

    Args:
        path (CloudPath): CloudPath object.
        data (dict | list): Data to be written.
        uid (str): User ID for logging.
        data_source (str): Data source for logging.

    Raises:
        JSONDecodeError: If there's an issue with JSON encoding.
        Exception: If writing to storage fails.
    """
    try:
        write_json_to_storage(path, data)
    except json.decoder.JSONDecodeError:
        structured_logger.warning(
            message="Failed to write activity summary to storage",
            uid=uid,
            data_source=data_source,
            traceback=traceback.format_exc(),
        )
        raise
    except Exception as e:
        structured_logger.error(
            message="Failed to write activity summary to storage",
            uid=uid,
            data_source=data_source,
            exception=str(e),
            traceback=traceback.format_exc(),
        )
        raise
