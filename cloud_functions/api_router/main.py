"""Main Entry point for cloud function."""
import json
import os
from typing import Dict, Optional

import functions_framework
import requests
from firebase_functions import https_fn
from google.cloud import functions_v2, run_v2

from .utils.logger_utils import log_structured


def invoke_cloud_function(
    function_name: str, payload: Dict, auth_header: Optional[str] = None
) -> https_fn.Response:
    """Invoke a Cloud Function using HTTPS.

    Args:
        function_name: Full resource name of the function
        payload: The JSON payload to send
        auth_header: Authorization header from original request

    Returns:
        https_fn.Response object with the function's response
    """
    try:
        # Get the function URL
        client = functions_v2.FunctionServiceClient()
        function = client.get_function(name=function_name)
        url = function.service_config.uri

        log_structured(
            "Invoking cloud function",
            url=url,
            payload=payload,
            target_function=function_name.split("/")[-1],
        )

        # For token refresh, we need to pass the data_source as a query parameter
        if "data_source" in payload:
            url = f"{url}?data_source={payload['data_source']}"
            log_structured("Modified URL with query params", url=url)

        # Prepare headers
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header

        # Make the request
        response = requests.post(url, json=payload, headers=headers)

        # Log the response details
        log_structured(
            "Received response",
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.text,
        )

        # Handle non-200 responses
        if response.status_code != 200:
            log_structured(
                "Non-200 response received",
                status_code=response.status_code,
                response_text=response.text,
                level="ERROR",
            )
            return https_fn.Response(
                status=response.status_code,
                response=response.text,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Try to parse JSON response
        try:
            if response.text:
                return https_fn.Response(
                    status=response.status_code,
                    response=json.dumps(response.json()),
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            return https_fn.Response(
                status=response.status_code,
                response=json.dumps({"message": response.text}),
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
            )
        except json.JSONDecodeError as e:
            log_structured(
                "Failed to parse JSON response",
                error=str(e),
                response_text=response.text,
                level="ERROR",
            )
            return https_fn.Response(
                status=500,
                response="Invalid JSON response from function",
                headers={"Access-Control-Allow-Origin": "*"},
            )

    except Exception as e:
        log_structured("Error invoking cloud function", error=str(e), level="ERROR")
        return https_fn.Response(
            status=500,
            response=str(e),
            headers={"Access-Control-Allow-Origin": "*"},
        )


def invoke_cloud_run(
    service_name: str, payload: Dict, auth_header: Optional[str] = None
) -> https_fn.Response:
    """Invoke a Cloud Run service using HTTPS.

    Args:
        service_name: Full resource name of the service
        payload: The JSON payload to send
        auth_header: Authorization header from original request

    Returns:
        https_fn.Response object with the service's response
    """
    try:
        # Get the service URL
        client = run_v2.ServicesClient()
        service = client.get_service(name=service_name)
        url = service.uri

        log_structured(
            "Invoking cloud run service",
            url=url,
            payload=payload,
            target_service=service_name.split("/")[-1],
        )

        # Prepare headers
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header

        # Make the request
        response = requests.post(url, json=payload, headers=headers)

        # Log the response details
        log_structured(
            "Received response",
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.text,
        )

        # Handle non-200 responses
        if response.status_code != 200:
            log_structured(
                "Non-200 response received",
                status_code=response.status_code,
                response_text=response.text,
                level="ERROR",
            )
            return https_fn.Response(
                status=response.status_code,
                response=response.text,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Try to parse JSON response
        try:
            if response.text:
                return https_fn.Response(
                    status=response.status_code,
                    response=json.dumps(response.json()),
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            return https_fn.Response(
                status=response.status_code,
                response=json.dumps({"message": response.text}),
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
            )
        except json.JSONDecodeError as e:
            log_structured(
                "Failed to parse JSON response",
                error=str(e),
                response_text=response.text,
                level="ERROR",
            )
            return https_fn.Response(
                status=500,
                response="Invalid JSON response from service",
                headers={"Access-Control-Allow-Origin": "*"},
            )

    except Exception as e:
        log_structured("Error invoking cloud run service", error=str(e), level="ERROR")
        return https_fn.Response(
            status=500,
            response=str(e),
            headers={"Access-Control-Allow-Origin": "*"},
        )


@functions_framework.http
def api_router(request):
    """Cloud function that acts as an API router.

    Routes requests to different endpoints based on the payload.
    """
    # Log all request details at the start
    log_structured(
        "Request received",
        method=request.method,
        headers=dict(request.headers),
        url=request.url,
        args=dict(request.args),
    )

    try:
        body = request.get_json(silent=True)
        log_structured("Request body", body=body)
    except Exception as e:
        log_structured("Error parsing request body", error=str(e), level="ERROR")

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

    try:
        # Get the request data
        request_data = request.get_json(silent=True)
        if not request_data:
            return https_fn.Response(
                status=400,
                response="Bad Request - No payload provided",
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Extract the target API and payload
        target_api = request_data.get("target_api")
        payload = request_data.get("payload", {})

        if not target_api:
            return https_fn.Response(
                status=400,
                response="Bad Request - No target API specified",
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Get project details from environment
        project_id = os.environ["PROJECT_ID"]
        region = os.environ["REGION"]
        environment = os.environ["ENVIRONMENT"]

        # Get authorization header
        auth_header = request.headers.get("Authorization")

        # Route to appropriate service
        if target_api == "token_refresh":
            function_name = f"projects/{project_id}/locations/{region}/functions/{environment}-token-refresh"
            return invoke_cloud_function(function_name, payload, auth_header)
        elif target_api == "data_run":
            service_name = f"projects/{project_id}/locations/{region}/services/{environment}-fitnessllm-dp"
            return invoke_cloud_run(service_name, payload, auth_header)
        else:
            return https_fn.Response(
                status=400,
                response=f"Bad Request - Invalid target API: {target_api}",
                headers={"Access-Control-Allow-Origin": "*"},
            )

    except Exception as e:
        log_structured("Error in api_router", error=str(e), level="ERROR")
        return https_fn.Response(
            status=500,
            response=str(e),
            headers={"Access-Control-Allow-Origin": "*"},
        )
