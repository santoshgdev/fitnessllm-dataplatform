import sys
from unittest import mock


def test_firebase_init(monkeypatch):
    import firebase_admin

    firebase_admin._apps.clear()

    with (
        mock.patch("firebase_admin.initialize_app") as mock_init,
        mock.patch(
            "cloud_functions.token_refresh.main.structured_logger.info"
        ) as mock_info,
    ):
        if "cloud_functions.token_refresh.main" in sys.modules:
            del sys.modules["cloud_functions.token_refresh.main"]
        import cloud_functions.token_refresh.main

        cloud_functions.token_refresh.main.firebase_init(service_name="test_service")
        # Check that our call was made, regardless of other calls
        mock_init.assert_any_call(name="test_service")
        mock_info.assert_any_call(
            message="Initializing Firebase Admin", service_name="test_service"
        )
        mock_info.assert_any_call(
            message="Firebase Admin initialized successfully",
            service_name="test_service",
        )
