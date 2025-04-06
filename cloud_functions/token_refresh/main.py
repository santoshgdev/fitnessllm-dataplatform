"""Main Entry point for cloud function."""
import os

from google.cloud import firestore
from firebase_admin import auth, initialize_app
from firebase_functions import firestore_fn, https_fn, options

from .streams.strava import strava_refresh_oauth_token
from .utils.logger_utils import logger

# Initialize Firebase Admin
initialize_app(options={
    'projectId': os.getenv("GOOGLE_CLOUD_PROJECT"),  # Replace with your actual project ID
})


@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins=["*"],
        cors_methods=["POST", "OPTIONS"]
    )
)
def token_refresh(request: https_fn.Request) -> https_fn.Response:
    """Cloud function taking http parameters to perform update of tokens.

    Args:
        request (http request): http request.

    Note: At current time, it registers the parameters uid (firebase user id) and data_source.
    """
    # Log all request details at the start
    logger.info("=== Request Details ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Args: {dict(request.args)}")
    try:
        body = request.get_json(silent=True)
        logger.info(f"Body: {body}")
    except Exception as e:
        logger.error(f"Error parsing body: {e}")
    logger.info("=== End Request Details ===")
    
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        return https_fn.Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Max-Age": "3600"
            }
        )

    body_data = request.get_json(silent=True)
    print(body_data)

    if not body_data or "data" not in body_data:
        return https_fn.Response(status=400, response="Required data is missing!")

    auth_header = request.headers.get('Authorization')
    logger.info(f"Received Authorization header: {auth_header}")
    if not auth_header or not auth_header.startswith('Bearer '):
        return https_fn.Response(status=400, response="Bad Request - Missing or invalid Authorization header")

    try:
        data = body_data["data"]
        data_source = data.get("data_source")
        if not data_source:
            return https_fn.Response(status=400, response="Bad Request - Missing data_source parameter")

        # Verify the Firebase ID token
        token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']  # Get uid from verified token

        db = firestore.Client()
        doc = db.collection("users").document(uid).get()
        
        if not doc.exists:
            return https_fn.Response(status=404, response=f'Not Found - User {uid} does not exist in Firestore')
            
        stream_data = doc.to_dict()[f"stream={data_source}"]
        
        if not stream_data or not stream_data.get("refreshToken"):
            return https_fn.Response(
                status=400,
                response=f'Bad Request - No refresh token found for user {uid} and data source {data_source}'
            )

        if data_source == "strava":
            try:
                strava_refresh_oauth_token(db, uid, stream_data["refreshToken"])
                return https_fn.Response(
                    status=200,
                    response="Token refreshed successfully for Strava."
                )
            except ValueError as e:
                if "credentials not found" in str(e):
                    return https_fn.Response(
                        status=500,
                        response="Internal Server Error - Strava credentials not found in Secret Manager"
                    )
                raise
        else:
            return https_fn.Response(
                status=400,
                response=f"Bad Request - Unsupported data source: {data_source}"
            )

    except auth.InvalidIdTokenError:
        return https_fn.Response(status=401, response="Unauthorized - Invalid token")
    except auth.ExpiredIdTokenError:
        return https_fn.Response(status=401, response="Unauthorized - Expired token")
    except auth.RevokedIdTokenError:
        return https_fn.Response(status=401, response="Unauthorized - Revoked token")
    except Exception as e:
        logger.error(f"Error in refresh_token: {str(e)}")
        return https_fn.Response(status=500, response=str(e))
