"""Main Entry point for Token Refresh."""
import json
import os

from firebase_admin import auth, initialize_app
from firebase_functions import https_fn, options
from google.cloud import firestore

from .streams.strava import strava_refresh_oauth_token
from .utils.logger_utils import partial_log_structured

initialize_app(
    options={
        "projectId": os.getenv("PROJECT_ID"),  # Replace with your actual project ID
    }
)


@https_fn.on_request(
    cors=options.CorsOptions(cors_origins=["*"], cors_methods=["POST", "OPTIONS"])
)
def token_refresh(request: https_fn.Request) -> https_fn.Response:
    """Cloud function taking http parameters to perform update of tokens.

    Args:
        request (http request): http request.

    Note: At current time, it registers the parameters uid (firebase user id) and data_source.
    """
    # Log all request details at the start
    partial_log_structured(
        message="Request received",
        method=request.method,
        headers=dict(request.headers),
        url=request.url,
        args=dict(request.args),
    )
    try:
        body = request.get_json(silent=True)
        partial_log_structured(message="Request body", body=body)
    except Exception as e:
        partial_log_structured(
            "Error parsing request body", error=str(e), level="ERROR"
        )

    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        return https_fn.Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Max-Age": "3600",
            },
        )

    # Get data_source from query parameters instead of body
    data_source = request.args.get("data_source")
    if not data_source:
        partial_log_structured(message="Missing data_source parameter", level="ERROR")
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

    auth_header = request.headers.get("Authorization")
    partial_log_structured(message="Received Authorization header", auth_header=auth_header)
    if not auth_header or not auth_header.startswith("Bearer "):
        partial_log_structured(message="Invalid Authorization header", level="ERROR")
        return https_fn.Response(
            status=400,
            response=json.dumps(
                {
                    "error": "Bad Request",
                    "message": "Bad Request - Missing or invalid Authorization header",
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )

    try:
        # Verify the Firebase ID token
        token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]  # Get uid from verified token
        partial_log_structured(message="Token verified", uid=uid)

        db = firestore.Client()
        doc = db.collection("users").document(uid).get()

        if not doc.exists:
            partial_log_structured(message="User not found", uid=uid, level="ERROR")
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

        stream_data = doc.to_dict()[f"stream={data_source}"]

        if not stream_data or not stream_data.get("refreshToken"):
            partial_log_structured(
                message="No refresh token found",
                uid=uid,
                data_source=data_source,
                level="ERROR",
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
                partial_log_structured(
                    message="Token refresh successful",
                    uid=uid,
                    data_source=data_source,
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
                    partial_log_structured(
                        message="Strava credentials not found",
                        error=str(e),
                        level="ERROR",
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
            partial_log_structured(
                message="Unsupported data source",
                data_source=data_source,
                level="ERROR",
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
        partial_log_structured(message="Invalid token", level="ERROR")
        return https_fn.Response(
            status=401,
            response=json.dumps(
                {"error": "Unauthorized", "message": "Unauthorized - Invalid token"}
            ),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except auth.ExpiredIdTokenError:
        partial_log_structured(message="Expired token", level="ERROR")
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
        partial_log_structured(message="Revoked token", level="ERROR")
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
        partial_log_structured(message="Error in token refresh", error=str(e), level="ERROR")
        return https_fn.Response(
            status=500,
            response=json.dumps({"error": "Internal Server Error", "message": str(e)}),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
