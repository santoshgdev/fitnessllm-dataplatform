"""Main entry point for cloud function."""
import functions_framework
from google.cloud import firestore
from firebase_admin import auth, initialize_app

from .streams.strava import strava_refresh_oauth_token
from .utils.logger_utils import logger

# Initialize Firebase Admin
initialize_app()

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

    try:
        # Verify the Firebase ID token
        token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']  # Get uid from verified token

        data_source = request.args.get("data_source")
        if not data_source:
            return {'error': 'Bad Request - Missing data_source parameter'}, 400

        db = firestore.Client()
        doc = db.collection("users").document(uid).get()
        
        if not doc.exists:
            return {'error': 'Not Found - User document does not exist'}, 404
            
        stream_data = doc.to_dict()[f"stream={data_source}"]
        
        if not stream_data or not stream_data.get("refreshToken"):
            return {'error': f'Not Found - No refresh token found for user {uid}'}, 404

        if data_source == "strava":
            try:
                strava_refresh_oauth_token(db, uid, stream_data["refreshToken"])
                return {"status": "success", "uid": uid}, 200
            except ValueError as e:
                if "credentials not found" in str(e):
                    return {'error': 'Strava credentials not found in Secret Manager'}, 400
                raise
        else:
            return {'error': 'Bad Request - Invalid data_source'}, 400

    except auth.InvalidIdTokenError:
        return {'error': 'Unauthorized - Invalid token'}, 401
    except auth.ExpiredIdTokenError:
        return {'error': 'Unauthorized - Token expired'}, 401
    except auth.RevokedIdTokenError:
        return {'error': 'Unauthorized - Token revoked'}, 401
    except Exception as e:
        logger.error(f"Error in refresh_token: {str(e)}")
        return {'error': 'Internal Server Error'}, 500
