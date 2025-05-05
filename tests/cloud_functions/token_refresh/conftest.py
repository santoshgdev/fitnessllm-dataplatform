"""Conftest for token refresh tests."""
import pytest


@pytest.fixture
def mock_request():
    """Mock request for testing."""

    class MockRequest:
        """Mock request for testing."""

        method = "POST"
        headers = {"Authorization": "Bearer test_token"}
        url = "fake_url"
        args = {"data_source": "strava"}

        def get_json(self):
            return {}

    return MockRequest()


@pytest.fixture
def mock_decoded_token():
    """Mock decoded token for testing."""
    return {"uid": "fake_user_id", "sub": "test_uid"}
