"""Utils to interact with cloud resources."""
import json
from os import environ

from cloudpathlib import CloudPath
from google.cloud import secretmanager

from fitnessllm_dataplatform.utils.logging_utils import logger


def create_resource_path(project_id: str, service: str, name: str) -> str:
    """Simple builder for resource paths."""
    return f"projects/{project_id}/{service}/{name}/versions/latest"


def get_secret(name: str) -> dict:
    """Retrieve secret from secret manager."""
    logger.debug("Initializing secret manager")
    client = secretmanager.SecretManagerServiceClient()
    logger.debug(f"Getting secret for {name}")
    response = client.access_secret_version(
        request={"name": create_resource_path(environ["PROJECT_ID"], "secrets", name)}
    )
    logger.debug(f"Retrieved secret {name}")
    secret_payload = response.payload.data.decode("UTF-8")
    return json.loads(secret_payload)


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
        logger.error(f"Failed to write data to storage: {e}")
        raise e
