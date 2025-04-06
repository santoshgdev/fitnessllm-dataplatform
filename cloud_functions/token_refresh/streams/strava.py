"""Strava specific utils."""
import os
import time
from os import environ

from beartype import beartype
from beartype.typing import Any, Dict
from google.cloud import firestore
from stravalib.client import Client

from ..utils.cloud_utils import get_secret
from ..utils.logger_utils import logger
from ..utils.task_utils import decrypt_token, encrypt_token, update_last_refresh


@beartype
def strava_refresh_oauth_token(
    db: firestore.Client, uid: str, refresh_token: str
) -> None:
    """Call Strava OAuth to refresh the token.

    Args:
        db: Firestore client.
        uid: Firestore user id.
        refresh_token: Encrypted Strava OAuth refresh token.

    Raises:
        ValueError: If refresh token is invalid.
    """
    encryption_key = get_secret(os.environ["ENCRYPTION_SECRET"])["token"]

    client = Client()
    strava_secret = get_secret(environ["STRAVA_SECRET"])
    client_id = strava_secret.get("client_id")
    client_secret = strava_secret.get("client_secret")

    if not client_id or not client_secret:
        raise ValueError("Strava credentials not found in Secret Manager")

    token_response = client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=decrypt_token(refresh_token, encryption_key),
    )

    current_time = time.time()
    expires_at = token_response["expires_at"]
    buffer_time = 14400  # 4 hours in seconds (since Strava tokens expire in 6 hours)
    time_until_expiration = expires_at - current_time

    logger.info(f"Current time: {current_time}")
    logger.info(f"Token expires at: {expires_at}")
    logger.info(f"Time until expiration: {time_until_expiration} seconds")

    # Refresh if less than 4 hours until expiration
    if time_until_expiration < buffer_time:
        new_tokens = {
            "accessToken": encrypt_token(
                token_response["access_token"], encryption_key
            ),
            "refreshToken": encrypt_token(
                token_response["refresh_token"], encryption_key
            ),
            "expiresAt": token_response["expires_at"],
            "lastTokenRefresh": update_last_refresh(),
        }

        strava_update_user_tokens(db=db, uid=uid, new_tokens=new_tokens)
        logger.info("Token has been refreshed")
    else:
        logger.info("Token is still valid")


@beartype
def strava_update_user_tokens(
    db: firestore.Client, uid: str, new_tokens: Dict[str, Any]
) -> None:
    """Update user document with new tokens.

    Args:
        db: Firestore client.
        uid: Firestore user id.
        new_tokens: New tokens.
    """
    user_ref = db.collection("users").document(uid)
    user_ref.update(
        {
            "stream=strava.accessToken": new_tokens["accessToken"],
            "stream=strava.refreshToken": new_tokens["refreshToken"],
            "stream=strava.expiresAt": new_tokens["expiresAt"],
        }
    )
