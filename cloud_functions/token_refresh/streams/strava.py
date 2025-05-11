"""Strava specific utils."""

from beartype.typing import Any, Dict
from fitnessllm_shared.logger_utils import structured_logger
from google.cloud import firestore


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
