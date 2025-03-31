import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from cloud_functions.token_refresh.main import refresh_token


def create_test_event(user_id: str) -> dict:
    """Create a test Cloud Event."""
    return {
        "data": {"message": {"data": json.dumps({"user_id": user_id}).encode("utf-8")}}
    }


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


@pytest.mark.cloud_function
def test_refresh_token_success(mock_strava_response, mock_strava_secret):
    """Test successful token refresh."""
    # Create test event
    test_event = create_test_event("test_user_123")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"refresh_token": "test_refresh_token"}

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_db), patch(
        "cloud_functions.token_refresh.streams.strava.Client.refresh_access_token", return_value=mock_strava_response
    ), patch("cloud_functions.token_refresh.utils.cloud_utils.get_secret", return_value=mock_strava_secret):
        # Call the function
        result = refresh_token(test_event)

        # Verify the result
        assert result["status"] == "success"
        assert result["user_id"] == "test_user_123"

        # Verify Firestore was called correctly
        mock_db.collection.assert_called_once_with("users")
        mock_ref.get.assert_called_once()
        mock_ref.update.assert_called_once_with(
            {
                "access_token": mock_strava_response["access_token"],
                "refresh_token": mock_strava_response["refresh_token"],
                "token_expires_at": mock_strava_response["expires_at"],
            }
        )


@pytest.mark.cloud_function
def test_refresh_token_user_not_found():
    """Test when user is not found."""
    test_event = create_test_event("nonexistent_user")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = False

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_db):
        # Verify it raises the correct error
        with pytest.raises(ValueError) as exc_info:
            refresh_token(test_event)
        assert str(exc_info.value) == "User nonexistent_user not found"


@pytest.mark.cloud_function
def test_refresh_token_missing_credentials():
    """Test when Strava credentials are missing."""
    test_event = create_test_event("test_user_123")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"refresh_token": "test_refresh_token"}

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_ref

    # Mock empty secret
    with patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_db), patch(
        "cloud_functions.token_refresh.utils.cloud_utils.get_secret", return_value={}
    ):
        # Verify it raises the correct error
        with pytest.raises(ValueError) as exc_info:
            refresh_token(test_event)
        assert str(exc_info.value) == "Strava credentials not found in Secret Manager"
