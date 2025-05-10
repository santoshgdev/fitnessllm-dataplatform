"""Cloud utils for api_router."""
import google.auth
import google.auth.transport.requests


def get_oauth_token() -> str:
    """Obtains an OAuth2 token for authenticating with Google Cloud Platform services.

    Unlike a Firebase ID token, which verifies user identity in Firebase Auth, this token grants access to GCP resources.

    Returns:
        An OAuth2 token as a string.
    """
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token
