"""Main Entry point for cloud function."""
import os
from typing import Dict

import requests
from firebase_admin import auth, initialize_app
from firebase_functions import https_fn, options
from google.cloud import functions, run

from .utils.logger_utils import logger

initialize_app(
    options={
        "projectId": os.getenv("PROJECT_ID"),
    }
)


def get_api_endpoints() -> Dict[str, str]:
    """Get API endpoints dynamically using service discovery.

    Returns:
        Dict[str, str]: Dictionary mapping API names to their URLs
    """
    try:
        project_id = os.getenv("PROJECT_ID")
        region = os.getenv("REGION")
        environment = os.getenv("ENVIRONMENT")

        # Initialize clients
        functions_client = functions.CloudFunctionsServiceClient()
        run_client = run.ServicesClient()

        # Get token refresh function URL
        token_refresh_name = f"projects/{project_id}/locations/{region}/functions/{environment}-token-refresh"
        token_refresh_function = functions_client.get_function(name=token_refresh_name)

        # Get data run service URL
        data_run_name = (
            f"projects/{project_id}/locations/{region}/services/{environment}-data-run"
        )
        data_run_service = run_client.get_service(name=data_run_name)

        return {
            "token_refresh": token_refresh_function.service_config.uri,
            "data_run": data_run_service.uri,
        }
    except Exception as e:
        logger.error(f"Error fetching API endpoints: {str(e)}")
        raise


@https_fn.on_request(
    cors=options.CorsOptions(cors_origins=["*"], cors_methods=["POST", "OPTIONS"])
)
def api_router(request: https_fn.Request) -> https_fn.Response:
    """Cloud function that acts as an API router.

    Routes requests to different endpoints based on the payload.
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
                "Access-Control-Max-Age": "3600",
            },
        )

    # Verify authentication
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return https_fn.Response(
            status=401,
            response="Unauthorized - Missing or invalid Authorization header",
        )

    try:
        # Verify the Firebase ID token
        # token = auth_header.split("Bearer ")[1]
        # decoded_token = auth.verify_id_token(token)

        # Get the request data
        request_data = request.get_json(silent=True)
        if not request_data:
            return https_fn.Response(
                status=400, response="Bad Request - No payload provided"
            )

        # Extract the target API and payload
        target_api = request_data.get("target_api")
        payload = request_data.get("payload", {})

        if not target_api:
            return https_fn.Response(
                status=400, response="Bad Request - No target API specified"
            )

        # Get API endpoints dynamically
        api_endpoints = get_api_endpoints()

        # Get the target URL
        target_url = api_endpoints.get(target_api)
        if not target_url:
            return https_fn.Response(
                status=400, response=f"Bad Request - Invalid target API: {target_api}"
            )

        # Make the request to the target API
        response = requests.post(
            target_url, json=payload, headers={"Content-Type": "application/json"}
        )

        # Return the response from the target API
        return https_fn.Response(
            status=response.status_code,
            response=response.text,
            headers={"Content-Type": "application/json"},
        )

    except auth.InvalidIdTokenError:
        return https_fn.Response(status=401, response="Unauthorized - Invalid token")
    except auth.ExpiredIdTokenError:
        return https_fn.Response(status=401, response="Unauthorized - Expired token")
    except auth.RevokedIdTokenError:
        return https_fn.Response(status=401, response="Unauthorized - Revoked token")
    except Exception as e:
        logger.error(f"Error in api_router: {str(e)}")
        return https_fn.Response(status=500, response=str(e))
