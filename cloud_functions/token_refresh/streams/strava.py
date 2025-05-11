"""Strava specific utils."""

from os import environ

from beartype import beartype
from beartype.typing import Any, Dict
from fitnessllm_shared.cloud_utils import get_secret
from fitnessllm_shared.logger_utils import structured_logger
from fitnessllm_shared.task_utils import (
    decrypt_token,
    encrypt_token,
    update_last_refresh,
)
from google.cloud import firestore
from pip._vendor.rich import traceback
from stravalib.client import Client


@beartype
def strava_refresh_oauth_token(
    db: firestore.Client,
    uid: str,
    refresh_token: str,
) -> None:
    """Call Strava OAuth to refresh the token.

    Args:
        db: Firestore client.
        uid: Firestore user id.
        refresh_token: Encrypted Strava OAuth refresh token.

    Raises:
        ValueError: If refresh token is invalid.
    """
    structured_logger(message="Starting token refresh", uid=uid)

    encryption_key = get_secret(environ["ENCRYPTION_SECRET"])["token"]

    client = Client()
    strava_secret = get_secret(environ["STRAVA_SECRET"])
    client_id = strava_secret.get("client_id")
    client_secret = strava_secret.get("client_secret")

    if not client_id or not client_secret:
        structured_logger.error(
            message="Strava credentials not found", service="token_refresh"
        )
        raise ValueError("Strava credentials not found in Secret Manager")

    try:
        token_response = client.refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=decrypt_token(refresh_token, encryption_key),
        )
        structured_logger.info(
            message="Token refresh successful", uid=uid, service="token_refresh"
        )

        new_tokens = {
            "accessToken": encrypt_token(
                token_response["access_token"],
                encryption_key,
            ),
            "refreshToken": encrypt_token(
                token_response["refresh_token"],
                encryption_key,
            ),
            "expiresAt": token_response["expires_at"],
            "lastTokenRefresh": update_last_refresh(),
        }

        strava_update_user_tokens(db=db, uid=uid, new_tokens=new_tokens)
        structured_logger.info(
            message="Tokens updated in Firestore", uid=uid, service="token_refresh"
        )
    except Exception as e:
        structured_logger.error(
            message="Error refreshing token",
            uid=uid,
            error=str(e),
            service="token_refresh",
            traceback=traceback.format_exc(),
        )
        raise


# Bear type is removed here due to a test that has a testing component located in tests/.
# This is done so that the testing components don't need to be shipped with the production code.
def strava_update_user_tokens(
    db: firestore.Client,
    uid: str,
    new_tokens: Dict[str, Any],
) -> None:
    """Update user document with new tokens.

    Args:
        db: Firestore client.
        uid: Firestore user id.
        new_tokens: New tokens.
    """
    structured_logger.info(
        message="Updating user tokens", uid=uid, service="token_refresh"
    )

    strava_ref = (
        db.collection("users").document(uid).collection("stream").document("strava")
    )

    doc = strava_ref.get()
    if not doc.exists:
        structured_logger.error(
            message="Strava document doesn't exist in stream subcollection",
            uid=uid,
            service="token_refresh",
        )
        # Create the document with default values
        strava_ref.set(new_tokens, merge=True)
        return

    strava_ref.update(
        {
            "accessToken": new_tokens["accessToken"],
            "refreshToken": new_tokens["refreshToken"],
            "expiresAt": new_tokens["expiresAt"],
            "lastTokenRefresh": new_tokens["lastTokenRefresh"],
        },
    )
    structured_logger.info(
        message="User tokens updated successfully", uid=uid, service="token_refresh"
    )
