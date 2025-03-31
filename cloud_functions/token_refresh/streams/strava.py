from typing import Dict, Any
from stravalib.client import Client
from cloud_functions.token_refresh.utils.cloud_utils import get_secret

def refresh_oauth_token(refresh_token: str) -> Dict[str, Any]:
    """Call Strava OAuth to refresh the token."""
    client = Client()

    strava_secret = get_secret("strava-credentials")
    client_id = strava_secret.get('client_id')
    client_secret = strava_secret.get('client_secret')
    
    if not client_id or not client_secret:
        raise ValueError("Strava credentials not found in Secret Manager")

    token_response = client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token
    )
    
    return {
        'accessToken': token_response['access_token'],
        'refreshToken': token_response['refresh_token'],
        'expiresAt': token_response['expires_at']
    }