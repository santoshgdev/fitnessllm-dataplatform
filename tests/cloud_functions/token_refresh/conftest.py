"""Conftest for token refresh tests."""

import pytest
from firebase_functions import https_fn


class MockRequest(https_fn.Request):
    """Mock request for testing."""

    method = "POST"
    headers = {"Authorization": "Bearer test_token"}
    url = "fake_url"
    args = {"data_source": "strava"}

    @staticmethod
    def get_json(*args, **kwargs) -> dict:
        """Returns a blank JSON object."""
        return {}


@pytest.fixture
def mock_request() -> "MockRequest":
    """Mock request for testing."""
    return MockRequest(environ={})


@pytest.fixture
def mock_decoded_token() -> dict[str, str]:
    """Mock decoded token for testing."""
    return {"uid": "fake_user_id", "sub": "test_uid"}
