"""Main Entry point for cloud function."""
import os
import json
from typing import Dict, Tuple, Any

import functions_framework
from google.cloud import functions, run
from google.cloud.functions.types import RunFunctionRequest
from google.cloud.run.types import SendRequestRequest

from .utils.logger_utils import logger


def invoke_cloud_function(function_name: str, payload: Dict) -> Tuple[Any, int]:
    """Invoke a Cloud Function directly using the SDK.

    Args:
        function_name: Full resource name of the function
        payload: The JSON payload to send

    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        client = functions.CloudFunctionsClient()

        # Create the request
        request = RunFunctionRequest()
        request.name = function_name
        request.data = json.dumps(payload).encode("utf-8")

        # Call the function
        response = client.run_function(request=request)

        # Parse the response
        response_data = json.loads(response.result.decode("utf-8"))
        return response_data, 200

    except Exception as e:
        logger.error(f"Error invoking cloud function: {str(e)}")
        return {"error": str(e)}, 500


def invoke_cloud_run(service_name: str, payload: Dict) -> Tuple[Any, int]:
    """Invoke a Cloud Run service directly using the SDK.

    Args:
        service_name: Full resource name of the service
        payload: The JSON payload to send

    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        client = run.ServicesClient()

        # Create the request
        request = SendRequestRequest()
        request.service = service_name
        request.body = json.dumps(payload).encode("utf-8")

        # Call the service
        response = client.send_request(request=request)

        # Parse the response
        response_data = json.loads(response.body.decode("utf-8"))
        return response_data, response.status_code

    except Exception as e:
        logger.error(f"Error invoking cloud run service: {str(e)}")
        return {"error": str(e)}, 500


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

        # Get project details from environment
        project_id = os.environ["PROJECT_ID"]
        region = os.environ["REGION"]
        environment = os.environ["ENVIRONMENT"]

        # Route to appropriate service
        if target_api == "token_refresh":
            function_name = f"projects/{project_id}/locations/{region}/functions/{environment}-token-refresh"
            response_data, status_code = invoke_cloud_function(function_name, payload)
        elif target_api == "data_run":
            service_name = f"projects/{project_id}/locations/{region}/services/{environment}-fitnessllm-dp"
            response_data, status_code = invoke_cloud_run(service_name, payload)
        else:
            return (
                f"Bad Request - Invalid target API: {target_api}",
                400,
                {"Access-Control-Allow-Origin": "*"},
            )

        # Return the response
        return (
            json.dumps(response_data),
            status_code,
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
