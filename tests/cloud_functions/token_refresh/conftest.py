from unittest.mock import  MagicMock
import pytest

@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock()
    request.method = "POST"
    request.args = {"data_source": "strava"}
    request.headers = {"Authorization": "Bearer mock_token"}
    request.get_json.return_value = {}
    return request

@pytest.fixture
def mock_decoded_token():
    """Create a mock decoded token."""
    return {
        "uid": "test_uid",
        "sub": "test_uid"
    }