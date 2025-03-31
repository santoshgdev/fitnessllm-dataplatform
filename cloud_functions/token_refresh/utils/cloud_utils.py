import json
import logging
from google.cloud import secretmanager
from os import environ
from typing import Dict, Any
from google.cloud import firestore


logger = logging.getLogger(__name__)

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

def create_resource_path(project_id: str, service: str, name: str) -> str:
    """Simple builder for resource paths."""
    return f"projects/{project_id}/{service}/{name}/versions/latest"


def get_refresh_token(user_doc: Dict[str, Any]) -> str:
    """Extract refresh token from user document."""
    return user_doc.get('refresh_token')

def update_user_tokens(db: firestore.Client, user_id: str, new_tokens: Dict[str, Any]) -> None:
    """Update user document with new tokens."""
    user_ref = db.collection("users").document(user_id)
    user_ref.update({
        'access_token': new_tokens['access_token'],
        'refresh_token': new_tokens['refresh_token'],
        'token_expires_at': new_tokens['expires_at']
    })