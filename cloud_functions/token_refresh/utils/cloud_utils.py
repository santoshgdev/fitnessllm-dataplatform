"""Cloud utils."""
import json
from os import environ

from beartype import beartype
from google.cloud import secretmanager
from utils.logger_utils import logger


@beartype
def get_secret(name: str) -> dict:
    """Retrieve secret from secret manager."""
    if "PROJECT_ID" not in environ:
        raise KeyError("PROJECT_ID environment variable is not set")
    logger.debug("Initializing secret manager")
    client = secretmanager.SecretManagerServiceClient()
    logger.debug(f"Getting secret for {name}")
    try:
        response = client.access_secret_version(
            request={
                "name": f"projects/{environ['PROJECT_ID']}/secrets/{name}/versions/latest"
            }
        )
        logger.debug(f"Retrieved secret {name}")
        secret_payload = response.payload.data.decode("UTF-8")
        return json.loads(secret_payload)
    except Exception as e:
        logger.error(f"Failed to retrieve or decode secret {name}: {e}")
        raise
