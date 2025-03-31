from typing import Dict, Any
from stravalib.client import Client
from cloud_functions.token_refresh.utils.cloud_utils import get_secret

def refresh_oauth_token(refresh_token: str) -> Dict[str, Any]:
    """Call Strava OAuth to refresh the token."""
    client = Client()
    
    # Get client credentials from Secret Manager
    strava_secret = get_secret("strava-credentials")
    client_id = strava_secret.get('client_id')
    client_secret = strava_secret.get('client_secret')
    
    if not client_id or not client_secret:
        raise ValueError("Strava credentials not found in Secret Manager")
    
    # Exchange refresh token for new access token
    token_response = client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token
    )
    
    return {
        'access_token': token_response['access_token'],
        'refresh_token': token_response['refresh_token'],
        'expires_at': token_response['expires_at']
    }