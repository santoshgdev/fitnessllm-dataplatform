"""Main entry point for cloud function."""
import functions_framework
from google.cloud import firestore
from firebase_admin import auth

from .streams.strava import strava_refresh_oauth_token
from .utils.logger_utils import logger


@functions_framework.http
def refresh_token(request):
    """Cloud function taking http parameters to perform update of tokens.

    Args:
        request (http request): http request.

    Note: At current time, it registers the parameters uid (firebase user id) and data_source.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return {'error': 'Unauthorized - No token provided'}, 401

    uid = auth_header.split('Bearer ')[1]

    try:
        data_source = request.args.get("data_source")

        db = firestore.Client()
        stream_data = (
            db.collection("users")
            .document(uid)
            .get()
            .to_dict()[f"stream={data_source}"]
        )

        if not refresh_token:
            raise ValueError(f"No refresh token found for user {uid}")
        if data_source == "strava":
            strava_refresh_oauth_token(db, uid, stream_data["refreshToken"])
            return {"status": "success", "uid": uid}
        else:
            raise Exception("Invalid data_source")

    except Exception as e:
        logger.error(f"Error in refresh_token: {str(e)}")
        raise
