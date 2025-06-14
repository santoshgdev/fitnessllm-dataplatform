"""Main Entry point for Token Refresh."""

import json
import traceback

import firebase_admin
from firebase_admin import auth
from firebase_functions import https_fn, options
from fitnessllm_shared.logger_utils import structured_logger
from fitnessllm_shared.streams.strava import strava_refresh_oauth_token
from google.cloud import firestore

from .entities.constants import CORS_HEADERS

service_name = "token_refresh"


def firebase_init(service_name: str = "default"):
    """Initialize Firebase Admin SDK."""
    structured_logger.info(
        message="Initializing Firebase Admin", service_name=service_name
    )
    if not firebase_admin._apps:
        try:
            firebase_admin.initialize_app(name=service_name)
            structured_logger.info(
                message="Firebase Admin initialized successfully",
                service_name=service_name,
            )
        except Exception as exc:
            structured_logger.error(
                message="Error initializing Firebase Admin",
                error=str(exc),
                traceback=traceback.format_exc(),
                service_name=service_name,
            )
            raise


firebase_init(service_name=service_name)


@https_fn.on_request(
    cors=options.CorsOptions(cors_origins=["*"], cors_methods=["POST", "OPTIONS"])
)
def token_refresh(request: https_fn.Request) -> https_fn.Response:
    """Handles HTTP requests to refresh OAuth tokens for a specified data source after verifying Firebase authentication.

    Validates the request, checks user and stream existence in Firestore, and refreshes the OAuth token (currently only for Strava). Responds with appropriate status codes and messages for authentication errors, missing parameters, unsupported data sources, or internal errors.
    """
    # Log all request details at the start
    structured_logger.info(
        message="Request received",
        method=request.method,
        headers=dict(request.headers),
        url=request.url,
        args=dict(request.args),
        service_name=service_name,
    )
    try:
        body = request.get_json(silent=True)
        structured_logger.info(
            message="Request body", body=body, service_name=service_name
        )
    except Exception as e:
        structured_logger.error(
            message="Error parsing request body",
            error=str(e),
            traceback=traceback.format_exc(),
            service_name=service_name,
        )

    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        return https_fn.Response(
            status=204,
            headers=CORS_HEADERS,
        )

    # Get data_source from query parameters instead of body
    data_source = request.args.get("data_source")
    if not data_source:
        structured_logger.error(
            message="Missing data_source parameter", service_name=service_name
        )
        return https_fn.Response(
            status=400,
            response=json.dumps(
                {
                    "error": "Bad Request",
                    "message": "Required data_source parameter is missing!",
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )

    try:
        # Log all headers for debugging
        all_headers = dict(request.headers)
        structured_logger.info(
            message="Received headers",
            headers=all_headers,
            auth_header=request.headers.get(
                "Authorization", "No Authorization header found"
            ),
            service_name=service_name,
        )

        # Get the Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            structured_logger.error(
                message="Invalid Authorization header",
                received_header=auth_header,
                service_name=service_name,
            )
            raise auth.InvalidIdTokenError("No valid authorization header found")

        # Extract the token from the Authorization header
        token = auth_header.split("Bearer ")[1]
        if not token:
            structured_logger.error(
                message="Empty Bearer token", service_name=service_name
            )
            raise auth.InvalidIdTokenError("Empty Bearer token")

        # Verify the Firebase ID token and log its contents
        decoded_token = auth.verify_id_token(token)
        structured_logger.info(
            message="Decoded token contents",
            token_empty=decoded_token is None or decoded_token == "",
            service_name=service_name,
        )

        uid = decoded_token.get("uid") or decoded_token.get("sub")
        if not uid:
            raise auth.InvalidIdTokenError("No uid or sub claim found in token")

        structured_logger.info(
            message="Token verified", uid=uid, service_name=service_name
        )

        db = firestore.Client()
        doc = db.collection("users").document(uid).get()

        if not doc.exists:
            structured_logger.error(
                message="User not found", uid=uid, service_name=service_name
            )
            return https_fn.Response(
                status=404,
                response=json.dumps(
                    {
                        "error": "Not Found",
                        "message": f"User {uid} does not exist in Firestore",
                    }
                ),
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        stream_doc = (
            db.collection("users")
            .document(uid)
            .collection("stream")
            .document(data_source)
            .get()
        )
        if not stream_doc.exists:
            # handle error (e.g., return 404 or similar)
            return https_fn.Response(
                status=404,
                response=json.dumps(
                    {
                        "error": "Not Found",
                        "message": f"Stream data for user {uid} and data source {data_source} not found",
                    }
                ),
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        stream_data = stream_doc.to_dict()

        if not stream_data or not stream_data.get("refreshToken"):
            structured_logger.error(
                message="No refresh token found",
                uid=uid,
                data_source=data_source,
                service_name=service_name,
            )
            return https_fn.Response(
                status=400,
                response=json.dumps(
                    {
                        "error": "Bad Request",
                        "message": f"Bad Request - No refresh token found for user {uid} and data source {data_source}",
                    }
                ),
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        if data_source == "strava":
            try:
                strava_refresh_oauth_token(db, uid, stream_data["refreshToken"])
                structured_logger.info(
                    message="Token refresh successful",
                    uid=uid,
                    data_source=data_source,
                    service_name=service_name,
                )
                return https_fn.Response(
                    status=200,
                    response=json.dumps(
                        {"message": "Token refreshed successfully for Strava."}
                    ),
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            except ValueError as e:
                if "credentials not found" in str(e):
                    structured_logger.error(
                        message="Strava credentials not found",
                        error=str(e),
                        level="ERROR",
                        traceback=traceback.format_exc(),
                        service_name=service_name,
                    )
                    return https_fn.Response(
                        status=500,
                        response=json.dumps(
                            {
                                "error": "Internal Server Error",
                                "message": "Internal Server Error - Strava credentials not found in Secret Manager",
                            }
                        ),
                        headers={
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                        },
                    )
                raise
        else:
            structured_logger.error(
                message="Unsupported data source",
                data_source=data_source,
                service_name=service_name,
            )
            return https_fn.Response(
                status=400,
                response=json.dumps(
                    {
                        "error": "Bad Request",
                        "message": f"Bad Request - Unsupported data source: {data_source}",
                    }
                ),
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
            )

    except auth.InvalidIdTokenError:
        structured_logger.error(
            message="Invalid Firebase ID Token; JWT Token Issue",
            auth=auth_header,
            traceback=traceback.format_exc(),
            service_name=service_name,
        )
        return https_fn.Response(
            status=401,
            response=json.dumps(
                {
                    "error": "Invalid Token",
                    "message": "Invalid Firebase ID Token; JWT Token Issue",
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except auth.ExpiredIdTokenError:
        structured_logger.error(
            message="Expired token",
            traceback=traceback.format_exc(),
            service_name=service_name,
        )
        return https_fn.Response(
            status=401,
            response=json.dumps(
                {"error": "Unauthorized", "message": "Unauthorized - Expired token"}
            ),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except auth.RevokedIdTokenError:
        structured_logger.error(
            message="Revoked token",
            traceback=traceback.format_exc(),
            service_name=service_name,
        )
        return https_fn.Response(
            status=401,
            response=json.dumps(
                {"error": "Unauthorized", "message": "Unauthorized - Revoked token"}
            ),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except Exception as e:
        structured_logger.error(
            message="Error in token refresh",
            error=str(e),
            traceback=traceback.format_exc(),
            service_name=service_name,
        )
        return https_fn.Response(
            status=500,
            response=json.dumps({"error": "Internal Server Error", "message": str(e)}),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
