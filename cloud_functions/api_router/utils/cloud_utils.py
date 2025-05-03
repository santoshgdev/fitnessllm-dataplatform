"""Cloud utils for api_router."""
import google.auth
import google.auth.transport.requests


def get_oauth_token() -> str:
    """Retrieve 0auth2 token."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token
