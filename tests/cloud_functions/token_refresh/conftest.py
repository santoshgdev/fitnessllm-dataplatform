"""Conftest for token refresh tests."""

import pytest


class MockRequest:
    """Mock request for testing."""

    method = "POST"
    headers = {"Authorization": "Bearer test_token"}
    url = "fake_url"
    args = {"data_source": "strava"}

    def get_json(self) -> dict:
        """Returns a blank JSON object."""
        return {}


@pytest.fixture
def mock_request() -> MockRequest:
    """Mock request for testing."""
    return MockRequest()


@pytest.fixture
def mock_decoded_token() -> dict[str, str]:
    """Mock decoded token for testing."""
    return {"uid": "fake_user_id", "sub": "test_uid"}
