import functions_framework
from google.cloud import firestore
import logging
from stravalib.client import Client
from google.cloud import secretmanager
from .firestore import get_refresh_token, update_user_tokens
from cloud_functions.token_refresh.streams.strava import refresh_oauth_token

logger = logging.getLogger(__name__)


@functions_framework.cloud_event
def refresh_token(cloud_event):
    """Cloud Function to refresh access token for a user."""
    try:
        data = cloud_event.data["message"]["data"]
        user_id = data.get("user_id")
        
        if not user_id:
            raise ValueError("No user_id provided in the message")

        db = firestore.Client()

        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise ValueError(f"User {user_id} not found")
            
        # Get refresh token from user document
        refresh_token = get_refresh_token(user_doc.to_dict())
        if not refresh_token:
            raise ValueError(f"No refresh token found for user {user_id}")

        new_tokens = refresh_oauth_token(refresh_token)

        update_user_tokens(db, user_id, new_tokens)
        
        logger.info(f"Successfully refreshed token for user {user_id}")
        return {"status": "success", "user_id": user_id}
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise 