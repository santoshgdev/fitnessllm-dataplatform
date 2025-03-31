import json
import sys
import os
from unittest.mock import MagicMock, patch
from flask import Request
from google.cloud import firestore

import pytest

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from cloud_functions.token_refresh.main import refresh_token


def create_test_request(user_id: str, data_source: str = "strava") -> Request:
    """Create a test Flask request object."""
    mock_request = MagicMock(spec=Request)
    mock_request.args = {
        "uid": user_id,
        "data_source": data_source
    }
    return mock_request


@pytest.fixture
def mock_strava_response():
    """Fixture for Strava token refresh response."""
    return {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_at": 1234567890,
    }


@pytest.fixture
def mock_strava_secret():
    """Fixture for Strava credentials secret."""
    return {"client_id": "test_client_id", "client_secret": "test_client_secret"}


@pytest.fixture
def mock_encryption_secret():
    """Fixture for encryption secret."""
    return {"token": "test_encryption_key"}


@pytest.fixture
def mock_firestore_client():
    """Fixture for Firestore client mock."""
    mock_client = MagicMock(spec=firestore.Client)
    return mock_client


@pytest.mark.cloud_function
def test_refresh_token_success(mock_strava_response, mock_strava_secret, mock_encryption_secret, mock_firestore_client):
    """Test successful token refresh."""
    # Create test request
    test_request = create_test_request("test_user_123")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "stream=strava": {
            "refreshToken": "test_refresh_token"
        }
    }

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_firestore_client.collection.return_value.document.return_value = mock_ref

    with patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_firestore_client), patch(
        "cloud_functions.token_refresh.streams.strava.Client.refresh_access_token", return_value=mock_strava_response
    ), patch("cloud_functions.token_refresh.utils.cloud_utils.get_secret", side_effect=[mock_strava_secret, mock_encryption_secret]), patch.dict(os.environ, {"ENCRYPTION_SECRET": "test_secret"}):
        # Call the function
        result = refresh_token(test_request)

        # Verify the result
        assert result["status"] == "success"
        assert result["uid"] == "test_user_123"

        # Verify Firestore was called correctly
        mock_firestore_client.collection.assert_called_once_with("users")
        mock_ref.get.assert_called_once()
        mock_ref.update.assert_called_once_with(
            {
                "access_token": mock_strava_response["access_token"],
                "refresh_token": mock_strava_response["refresh_token"],
                "token_expires_at": mock_strava_response["expires_at"],
            }
        )


@pytest.mark.cloud_function
def test_refresh_token_user_not_found(mock_firestore_client):
    """Test when user is not found."""
    test_request = create_test_request("nonexistent_user")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = False

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_firestore_client.collection.return_value.document.return_value = mock_ref

    with patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_firestore_client), patch.dict(os.environ, {"ENCRYPTION_SECRET": "test_secret"}):
        # Verify it raises the correct error
        with pytest.raises(ValueError) as exc_info:
            refresh_token(test_request)
        assert str(exc_info.value) == "User nonexistent_user not found"


@pytest.mark.cloud_function
def test_refresh_token_missing_credentials(mock_firestore_client, mock_encryption_secret):
    """Test when Strava credentials are missing."""
    test_request = create_test_request("test_user_123")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "stream=strava": {
            "refreshToken": "test_refresh_token"
        }
    }

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_firestore_client.collection.return_value.document.return_value = mock_ref

    # Mock empty secret
    with patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_firestore_client), patch(
        "cloud_functions.token_refresh.utils.cloud_utils.get_secret", side_effect=[{}, mock_encryption_secret]
    ), patch.dict(os.environ, {"ENCRYPTION_SECRET": "test_secret"}):
        # Verify it raises the correct error
        with pytest.raises(ValueError) as exc_info:
            refresh_token(test_request)
        assert str(exc_info.value) == "Strava credentials not found in Secret Manager"
