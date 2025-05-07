"""Strava specific utils."""
import os
from os import environ

from beartype import beartype
from beartype.typing import Any, Dict
from google.cloud import firestore
from stravalib.client import Client

from ..shared.cloud_utils import get_secret
from ..shared.logger_utils import partial_log_structured
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
    partial_log_structured(message="Starting token refresh", uid=uid)

    encryption_key = get_secret(os.environ["ENCRYPTION_SECRET"])["token"]

    client = Client()
    strava_secret = get_secret(environ["STRAVA_SECRET"])
    client_id = strava_secret.get("client_id")
    client_secret = strava_secret.get("client_secret")

    if not client_id or not client_secret:
        partial_log_structured(message="Strava credentials not found", level="ERROR")
        raise ValueError("Strava credentials not found in Secret Manager")

    try:
        token_response = client.refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=decrypt_token(refresh_token, encryption_key),
        )
        partial_log_structured(message="Token refresh successful", uid=uid)

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
        partial_log_structured(message="Tokens updated in Firestore", uid=uid)
    except Exception as e:
        partial_log_structured(
            message="Error refreshing token",
            uid=uid,
            error=str(e),
            level="ERROR",
        )
        raise


# Bear type is removed here due to a test that has a testing component located in tests/.
# This is done so that the testing components don't need to be shipped with the production code.
def strava_update_user_tokens(
    db: firestore.Client, uid: str, new_tokens: Dict[str, Any]
) -> None:
    """Update user document with new tokens.

    Args:
        db: Firestore client.
        uid: Firestore user id.
        new_tokens: New tokens.
    """
    partial_log_structured(message="Updating user tokens", uid=uid)
    # Get the reference to the strava document in the stream subcollection
    strava_ref = (
        db.collection("users").document(uid).collection("stream").document("strava")
    )

    doc = strava_ref.get()
    if not doc.exists:
        partial_log_structured(
            message="Strava document doesn't exist in stream subcollection",
            uid=uid,
            level="ERROR",
        )
        # Create the document with default values
        strava_ref.set(new_tokens)
        return

    strava_ref.update(
        {
            "accessToken": new_tokens["accessToken"],
            "refreshToken": new_tokens["refreshToken"],
            "expiresAt": new_tokens["expiresAt"],
            "lastTokenRefresh": new_tokens["lastTokenRefresh"],
        }
    )
    partial_log_structured(message="User tokens updated successfully", uid=uid)
