import json
import sys
import os
from unittest.mock import MagicMock, patch
from flask import Request
from google.cloud import firestore
import base64

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


@pytest.fixture
def mock_env():
    """Fixture for environment variables."""
    return {
        "ENCRYPTION_SECRET": "test_secret",
        "PROJECT_ID": "test-project-id",
        "STRAVA_SECRET": "test_strava_secret"
    }


@pytest.fixture
def mock_secret_manager():
    """Fixture for Secret Manager client mock."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.payload.data = json.dumps({"token": "test_encryption_key"}).encode()
    mock_client.access_secret_version.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_encrypted_token():
    """Fixture for encrypted token in the correct format."""
    # Create a 16-byte IV (required for AES-256-CBC)
    iv = base64.b64encode(b"0123456789abcdef").decode('utf-8')
    # Create encrypted data that is a multiple of 16 bytes (AES block size)
    encrypted_data = base64.b64encode(b"test_encrypted_data_padded_to_16_bytes").decode('utf-8')
    return f"{iv}:{encrypted_data}"


@pytest.mark.cloud_function
def test_refresh_token_success(mock_strava_response, mock_strava_secret, mock_encryption_secret, mock_firestore_client, mock_env, mock_secret_manager, mock_encrypted_token):
    """Test successful token refresh."""
    # Create test request
    test_request = create_test_request("test_user_123")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "stream=strava": {
            "refreshToken": mock_encrypted_token
        }
    }

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_firestore_client.collection.return_value.document.return_value = mock_ref

    # Mock get_secret to return different values based on the secret name
    def get_secret_side_effect(secret_name):
        if secret_name == "test_strava_secret":
            return mock_strava_secret
        elif secret_name == "test_secret":
            return mock_encryption_secret
        return {}

    # Mock decrypt_token first to ensure it's mocked before any other operations
    with patch("cloud_functions.token_refresh.streams.strava.decrypt_token", return_value="decrypted_refresh_token"), \
         patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_firestore_client), \
         patch("cloud_functions.token_refresh.streams.strava.Client", autospec=True) as mock_client_class, \
         patch("cloud_functions.token_refresh.utils.cloud_utils.get_secret", side_effect=get_secret_side_effect), \
         patch.dict(os.environ, mock_env), \
         patch("cloud_functions.token_refresh.utils.cloud_utils.secretmanager.SecretManagerServiceClient", return_value=mock_secret_manager), \
         patch("cloud_functions.token_refresh.streams.strava.get_secret", side_effect=get_secret_side_effect), \
         patch("cloud_functions.token_refresh.streams.strava.encrypt_token", side_effect=lambda token, _: f"encrypted_{token}"):
        
        # Set up the mock client instance
        mock_client_instance = mock_client_class.return_value
        mock_client_instance.refresh_access_token.return_value = mock_strava_response

        # Call the function
        result = refresh_token(test_request)

        # Verify the result
        assert result["status"] == "success"
        assert result["uid"] == "test_user_123"

        # Verify Firestore was called correctly
        mock_firestore_client.collection.assert_any_call("users")
        mock_ref.get.assert_called_once()
        mock_ref.update.assert_called_once_with(
            {
                "stream=strava.accessToken": f"encrypted_{mock_strava_response['access_token']}",
                "stream=strava.refreshToken": f"encrypted_{mock_strava_response['refresh_token']}",
                "stream=strava.expiresAt": mock_strava_response["expires_at"],
            }
        )


@pytest.mark.cloud_function
def test_refresh_token_user_not_found(mock_strava_response, mock_firestore_client, mock_env, mock_secret_manager, mock_strava_secret, mock_encryption_secret, mock_encrypted_token):
    """Test when user is not found."""
    test_request = create_test_request("nonexistent_user")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc.to_dict.return_value = None  # Document doesn't exist, so to_dict returns None

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_firestore_client.collection.return_value.document.return_value = mock_ref

    # Mock get_secret to return different values based on the secret name
    def get_secret_side_effect(secret_name):
        if secret_name == "test_strava_secret":
            return mock_strava_secret
        elif secret_name == "test_secret":
            return mock_encryption_secret
        return {}

    # Mock decrypt_token first to ensure it's mocked before any other operations
    with patch("cloud_functions.token_refresh.streams.strava.decrypt_token", return_value="decrypted_refresh_token"), \
         patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_firestore_client), \
         patch("cloud_functions.token_refresh.streams.strava.Client", autospec=True) as mock_client_class, \
         patch("cloud_functions.token_refresh.utils.cloud_utils.get_secret", side_effect=get_secret_side_effect), \
         patch.dict(os.environ, mock_env), \
         patch("cloud_functions.token_refresh.utils.cloud_utils.secretmanager.SecretManagerServiceClient", return_value=mock_secret_manager), \
         patch("cloud_functions.token_refresh.streams.strava.get_secret", side_effect=get_secret_side_effect), \
         patch("cloud_functions.token_refresh.streams.strava.encrypt_token", side_effect=lambda token, _: f"encrypted_{token}"):
        
        # Set up the mock client instance
        mock_client_instance = mock_client_class.return_value
        mock_client_instance.refresh_access_token.return_value = mock_strava_response

        # Verify it raises the correct error
        with pytest.raises(TypeError) as exc_info:
            refresh_token(test_request)
        assert str(exc_info.value) == "'NoneType' object is not subscriptable"

        # Verify Firestore was called correctly
        mock_firestore_client.collection.assert_any_call("users")
        mock_ref.get.assert_called_once()
        mock_ref.update.assert_not_called()


@pytest.mark.cloud_function
def test_refresh_token_missing_credentials(mock_strava_response, mock_firestore_client, mock_encryption_secret, mock_env, mock_secret_manager, mock_encrypted_token):
    """Test when Strava credentials are missing."""
    test_request = create_test_request("test_user_123")

    # Mock Firestore client and document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "stream=strava": {
            "refreshToken": mock_encrypted_token
        }
    }

    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc

    mock_firestore_client.collection.return_value.document.return_value = mock_ref

    # Mock get_secret to return empty dict for Strava secret
    def get_secret_side_effect(secret_name):
        if secret_name == "test_strava_secret":
            return {}
        elif secret_name == "test_secret":
            return mock_encryption_secret
        return {}

    # Mock decrypt_token first to ensure it's mocked before any other operations
    with patch("cloud_functions.token_refresh.streams.strava.decrypt_token", return_value="decrypted_refresh_token"), \
         patch("cloud_functions.token_refresh.main.firestore.Client", return_value=mock_firestore_client), \
         patch("cloud_functions.token_refresh.streams.strava.Client", autospec=True) as mock_client_class, \
         patch("cloud_functions.token_refresh.utils.cloud_utils.get_secret", side_effect=get_secret_side_effect), \
         patch.dict(os.environ, mock_env), \
         patch("cloud_functions.token_refresh.utils.cloud_utils.secretmanager.SecretManagerServiceClient", return_value=mock_secret_manager), \
         patch("cloud_functions.token_refresh.streams.strava.get_secret", side_effect=get_secret_side_effect), \
         patch("cloud_functions.token_refresh.streams.strava.encrypt_token", side_effect=lambda token, _: f"encrypted_{token}"):
        
        # Set up the mock client instance
        mock_client_instance = mock_client_class.return_value
        mock_client_instance.refresh_access_token.return_value = mock_strava_response

        # Verify it raises the correct error
        with pytest.raises(ValueError) as exc_info:
            refresh_token(test_request)
        assert str(exc_info.value) == "Strava credentials not found in Secret Manager"
