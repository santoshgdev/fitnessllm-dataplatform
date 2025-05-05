from cloud_functions.token_refresh.streams.strava import strava_update_user_tokens
from tests.cloud_functions.testing_utils import InMemoryFirestoreClient


def test_strava_update_user_tokens():
    db = InMemoryFirestoreClient()
    uid = "testuser123"

    db.collection("users").document(uid).collection("stream").document("strava").set(
        {
            "accessToken": "old_access_token",
            "refreshToken": "old_refresh_token",
            "expiresAt": 123456,
            "lastTokenRefresh": "old_time",
        }
    )
    new_tokens = {
        "accessToken": "new_access_token",
        "refreshToken": "new_refresh_token",
        "expiresAt": 654321,
        "lastTokenRefresh": "new_time",
    }
    strava_update_user_tokens(db, uid, new_tokens)

    updated_doc = (
        db.collection("users")
        .document(uid)
        .collection("stream")
        .document("strava")
        .get()
    )
    updated_data = updated_doc.to_dict()
    assert updated_data["accessToken"] == "new_access_token"
    assert updated_data["refreshToken"] == "new_refresh_token"
    assert updated_data["expiresAt"] == 654321
    assert updated_data["lastTokenRefresh"] == "new_time"
