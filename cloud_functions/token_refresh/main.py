"""Main entry point for cloud function."""
import functions_framework
from google.cloud import firestore
from firebase_admin import auth, initialize_app
from flask import make_response

from .streams.strava import strava_refresh_oauth_token
from .utils.logger_utils import logger

# Initialize Firebase Admin
initialize_app()

# Define allowed origins
ALLOWED_ORIGINS = [
    'https://fitnessllm.app',  # Production domain
    'https://www.fitnessllm.app',  # Production domain with www
    'http://localhost:3000',  # Local development
    'http://localhost:8081', # Local development
    'https://dev.fitnessllm.app',  # Development domain
]

def cors_enabled_function(request):
    """Handle CORS preflight requests and add CORS headers to responses."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Get the origin from the request
    origin = request.headers.get('Origin')
    
    # Check if the origin is allowed
    if origin not in ALLOWED_ORIGINS:
        return {'error': 'Forbidden - Origin not allowed'}, 403

    # Add CORS headers to the response
    headers = {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    }

    return headers

@functions_framework.http
def refresh_token(request):
    """Cloud function taking http parameters to perform update of tokens.

    Args:
        request (http request): http request.

    Note: At current time, it registers the parameters uid (firebase user id) and data_source.
    """
    # Handle CORS
    # cors_headers = cors_enabled_function(request)
    # if isinstance(cors_headers, tuple):
    #     return cors_headers

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return {'error': 'Unauthorized - No token provided'}, 401#, cors_headers

    try:
        # Verify the Firebase ID token
        token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']  # Get uid from verified token

        data_source = request.args.get("data_source")
        if not data_source:
            return {'error': 'Bad Request - Missing data_source parameter'}, 400#, cors_headers

        db = firestore.Client()
        doc = db.collection("users").document(uid).get()
        
        if not doc.exists:
            return {'error': 'Not Found - User document does not exist'}, 404#, cors_headers
            
        stream_data = doc.to_dict()[f"stream={data_source}"]
        
        if not stream_data or not stream_data.get("refreshToken"):
            return {'error': f'Not Found - No refresh token found for user {uid}'}, 404#, cors_headers

        if data_source == "strava":
            try:
                strava_refresh_oauth_token(db, uid, stream_data["refreshToken"])
                return {"status": "success", "uid": uid}, 200#, cors_headers
            except ValueError as e:
                if "credentials not found" in str(e):
                    return {'error': 'Strava credentials not found in Secret Manager'}, 400#, cors_headers
                raise
        else:
            return {'error': 'Bad Request - Invalid data_source'}, 400#, cors_headers

    except auth.InvalidIdTokenError:
        return {'error': 'Unauthorized - Invalid token'}, 401#, cors_headers
    except auth.ExpiredIdTokenError:
        return {'error': 'Unauthorized - Token expired'}, 401#, cors_headers
    except auth.RevokedIdTokenError:
        return {'error': 'Unauthorized - Token revoked'}, 401#, cors_headers
    except Exception as e:
        logger.error(f"Error in refresh_token: {str(e)}")
        return {'error': 'Internal Server Error'}, 500#, cors_headers
