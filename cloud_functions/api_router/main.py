"""Main Entry point for cloud function."""
import os
from typing import Dict

import functions_framework
import requests
from google.cloud import functions, run

from .utils.logger_utils import logger


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
        run_service = run_client.get_service(name=data_run_name)

        return {
            "token_refresh": token_refresh_function.service_config.uri,
            "data_run": run_service.uri,
        }
    except Exception as e:
        logger.error(f"Error fetching API endpoints: {str(e)}")
        raise


@functions_framework.http
def api_router(request):
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
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    try:
        # Get the request data
        request_data = request.get_json(silent=True)
        if not request_data:
            return (
                "Bad Request - No payload provided",
                400,
                {"Access-Control-Allow-Origin": "*"},
            )

        # Extract the target API and payload
        target_api = request_data.get("target_api")
        payload = request_data.get("payload", {})

        if not target_api:
            return (
                "Bad Request - No target API specified",
                400,
                {"Access-Control-Allow-Origin": "*"},
            )

        # Get API endpoints dynamically
        api_endpoints = get_api_endpoints()

        # Get the target URL
        target_url = api_endpoints.get(target_api)
        if not target_url:
            return (
                f"Bad Request - Invalid target API: {target_api}",
                400,
                {"Access-Control-Allow-Origin": "*"},
            )

        # Make the request to the target API
        # Forward any Authorization header if present
        headers = {"Content-Type": "application/json"}
        if "Authorization" in request.headers:
            headers["Authorization"] = request.headers["Authorization"]

        response = requests.post(
            target_url,
            json=payload,
            headers=headers
        )

        # Return the response from the target API
        return (
            response.text,
            response.status_code,
            {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )

    except Exception as e:
        logger.error(f"Error in api_router: {str(e)}")
        return (
            str(e),
            500,
            {"Access-Control-Allow-Origin": "*"},
        )

