"""Cloud utils for api_router."""
import google.auth
import google.auth.transport.requests


def get_oauth_token() -> str:
    """Retrieve Oauth2 token.

    This is needed to authenticate to various GCP services. Opposed to Firebase ID token, which is just used to verify
    whether the user is in firebase auth.
    """
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token
