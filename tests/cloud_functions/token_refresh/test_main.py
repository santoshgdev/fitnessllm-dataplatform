import json
from unittest.mock import patch

import flask
from firebase_admin import auth

from cloud_functions.token_refresh.main import token_refresh

# Import your in-memory Firestore and population function
from tests.cloud_functions.testing_utils import (
    populate_inmemory_firestore_with_users_and_streams,
)


@patch(
    "cloud_functions.token_refresh.main.partial_log_structured",
    new=lambda *a, **kw: None,
)
@patch(
    "cloud_functions.token_refresh.main.strava_refresh_oauth_token",
    new=lambda *a, **kw: None,
)
@patch("firebase_admin.auth.verify_id_token")
def test_token_refresh_success(mock_verify, mock_request, mock_decoded_token):
    # Setup in-memory Firestore with one user and strava stream
    db, user_ids = populate_inmemory_firestore_with_users_and_streams(num_users=1)
    user_id = user_ids[0]
    mock_decoded_token["uid"] = user_id
    mock_verify.return_value = mock_decoded_token

    with patch("google.cloud.firestore.Client", return_value=db):
        app = flask.Flask(__name__)
        with app.app_context():
            with app.test_request_context(
                path="/",
                method="POST",
                headers={"Authorization": "Bearer test_token"},
                query_string={"data_source": "strava"},
                json={},
            ):
                response = token_refresh(mock_request)
                assert response.status_code == 200
                assert (
                    "Token refreshed successfully for Strava"
                    in json.loads(response.response[0])["message"]
                )


@patch(
    "cloud_functions.token_refresh.main.partial_log_structured",
    new=lambda *a, **kw: None,
)
@patch(
    "cloud_functions.token_refresh.main.strava_refresh_oauth_token",
    new=lambda *a, **kw: None,
)
@patch("firebase_admin.auth.verify_id_token")
def test_token_refresh_missing_data_source(
    mock_verify, mock_request, mock_decoded_token
):
    """Test token refresh with missing data source."""

    # Setup in-memory Firestore with one user and strava stream
    db, user_ids = populate_inmemory_firestore_with_users_and_streams(num_users=1)
    user_id = user_ids[0]
    mock_decoded_token["uid"] = user_id
    mock_verify.return_value = mock_decoded_token

    with patch("google.cloud.firestore.Client", return_value=db):
        app = flask.Flask(__name__)
        with app.app_context():
            with app.test_request_context(
                path="/",
                method="POST",
                headers={"Authorization": "Bearer test_token"},
                query_string={"data_source": "strava"},
                json={},
            ):
                mock_request.args = {}
                response = token_refresh(mock_request)
                assert response.status_code == 400
                assert (
                    "Required data_source parameter is missing"
                    in json.loads(response.response[0])["message"]
                )


@patch(
    "cloud_functions.token_refresh.main.partial_log_structured",
    new=lambda *a, **kw: None,
)
@patch(
    "cloud_functions.token_refresh.main.strava_refresh_oauth_token",
    new=lambda *a, **kw: None,
)
@patch("firebase_admin.auth.verify_id_token")
def test_token_refresh_invalid_token(mock_verify, mock_request, mock_decoded_token):
    """Test token refresh with invalid token."""

    # Setup in-memory Firestore with one user and strava stream
    db, user_ids = populate_inmemory_firestore_with_users_and_streams(num_users=1)
    user_id = user_ids[0]
    mock_decoded_token["uid"] = user_id
    mock_verify.return_value = mock_decoded_token

    with patch("google.cloud.firestore.Client", return_value=db):
        app = flask.Flask(__name__)
        with app.app_context():
            with app.test_request_context(
                path="/",
                method="POST",
                headers={"Authorization": "Bearer test_token"},
                query_string={"data_source": "strava"},
                json={},
            ):
                mock_verify.side_effect = auth.InvalidIdTokenError("Invalid token")
                response = token_refresh(mock_request)
                assert response.status_code == 401
                assert (
                    "Invalid Firebase ID Token; JWT Token Issu"
                    in json.loads(response.response[0])["message"]
                )
