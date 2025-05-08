"""Cloud utils."""
import json
from os import environ

from beartype import beartype
from google.cloud import secretmanager

from ..shared.logger_utils import create_structured_logger

structured_logger = create_structured_logger(__name__)


@beartype
def get_secret(name: str) -> dict:
    """Retrieve secret from secret manager."""
    if "PROJECT_ID" not in environ:
        raise KeyError("PROJECT_ID environment variable not found")
    structured_logger(message="Initializing secret manager")
    client = secretmanager.SecretManagerServiceClient()
    structured_logger(message=f"Getting secret for {name}")
    try:
        response = client.access_secret_version(
            request={
                "name": f"projects/{environ['PROJECT_ID']}/secrets/{name}/versions/latest",
            }
        )
        structured_logger(message=f"Retrieved secret {name}")
        secret_payload = response.payload.data.decode("UTF-8")
        return json.loads(secret_payload)
    except Exception as e:
        structured_logger(message=f"Failed to retrieve or decode secret {name}: {e}")
        raise
