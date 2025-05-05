from unittest.mock import  MagicMock
import pytest



@pytest.fixture
def mock_request():
    class MockRequest:
        method = "POST"
        headers = {"Authorization": "Bearer test_token"}
        url = "fake_url"
        args = {"data_source": "strava"}
        def get_json(self):
            return {}
    return MockRequest()

@pytest.fixture
def mock_decoded_token():
    return {"uid": "fake_user_id", "sub": "test_uid"}