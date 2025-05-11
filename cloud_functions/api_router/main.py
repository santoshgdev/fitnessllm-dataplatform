"""Main Entry point for API Router."""

import json
import os
import traceback
from typing import Dict, Optional

import firebase_admin
import functions_framework
import requests
from firebase_functions import https_fn
from fitnessllm_shared.logger_utils import structured_logger
from google.cloud import functions_v2

from .utils.cloud_utils import get_oauth_token

try:
    firebase_admin.initialize_app()
    structured_logger(message="Firebase Admin initialized successfully")
except Exception as e:
    structured_logger.error(
        message="Error initializing Firebase Admin",
        error=str(e),
        traceback=traceback.format_exc(),
        service="api_router",
    )
    raise


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

        structured_logger.info(
            message="Attempting to invoke cloud function",
            url=url,
            payload=payload,
            auth_header=auth_header,
            service="api_router",
        )

        # Prepare headers with auth if provided
        headers = {"Content-Type": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header
        structured_logger.info(
            message="Invoking cloud function",
            url=url,
            payload=payload,
            auth_header_present="Authorization" in headers,
            headers=headers,
            service="api_router",
        )

        # For token refresh, we need to pass the data_source as a query parameter
        if "data_source" in payload:
            url = f"{url}?data_source={payload['data_source']}"
            structured_logger.info(
                message="Modified URL with query params", url=url, service="api_router"
            )

        # Make the request
        response = requests.post(url=url, json=payload, headers=headers, timeout=10)

        # Log the response details
        structured_logger.info(
            message="Received response",
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.text,
            service="api_router",
        )

        # Handle non-200 responses
        if response.status_code != 200:
            structured_logger.error(
                message="Non-200 response received when attempting to invoke cloud function",
                status_code=response.status_code,
                response_text=response.text,
                service="api_router",
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
            structured_logger.error(
                message="Failed to parse JSON response",
                error=str(e),
                response_text=response.text,
                traceback=traceback.format_exc(),
                service="api_router",
            )
            return https_fn.Response(
                status=500,
                response="Invalid JSON response from function",
                headers={"Access-Control-Allow-Origin": "*"},
            )

    except Exception as e:
        structured_logger.error(
            message="Error invoking cloud function",
            error=str(e),
            traceback=traceback.format_exc(),
            service="api_router",
        )
        return https_fn.Response(
            status=500,
            response=str(e),
            headers={"Access-Control-Allow-Origin": "*"},
        )


def invoke_cloud_run_job(service_name: str, payload: Dict) -> https_fn.Response:
    """Invoke a Cloud Run service using HTTPS.

    Args:
        service_name: Full resource name of the service
        payload: The JSON payload to send
        auth_header: Authorization header from original request

    Returns:
        https_fn.Response object with the service's response
    """
    try:
        project_id = os.environ["PROJECT_ID"]
        region = os.environ["REGION"]
        environment = os.environ["ENVIRONMENT"]
        url = (
            f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
            f"namespaces/{project_id}/jobs/{environment}-fitnessllm-dp:run"
        )

        structured_logger.info(
            message="Invoking cloud run service",
            url=url,
            payload=payload,
            target_service=service_name.split("/")[-1],
            service="api_router",
        )

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_oauth_token()}",
        }
        # Use the correct overrides structure for Cloud Run jobs

        if "uid" not in payload:
            raise ValueError("Payload is missing uid.")

        new_payload = {
            "overrides": {
                "taskCount": 1,
                "containerOverrides": [
                    {
                        "args": [
                            "python",
                            "-m",
                            "fitnessllm_dataplatform.task_handler",
                            "full_etl",
                            f"--uid={payload['uid']}",
                            "--data_source=STRAVA",
                        ]
                    }
                ],
            }
        }

        # Make the request
        response = requests.post(url, json=new_payload, headers=headers)

        # Log the response details
        structured_logger.info(
            message="Received response",
            status_code=response.status_code,
            headers=headers,
            content=response.text,
            service="api_router",
        )

        # Handle non-200 responses
        if response.status_code != 200:
            structured_logger.error(
                message="Non-200 response received when attempting to invoke cloud run service",
                status_code=response.status_code,
                response_text=response.text,
                service="api_router",
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
            structured_logger.error(
                message="Failed to parse JSON response",
                error=str(e),
                response_text=response.text,
                traceback=traceback.format_exc(),
                service="api_router",
            )
            return https_fn.Response(
                status=500,
                response="Invalid JSON response from service",
                headers={"Access-Control-Allow-Origin": "*"},
            )

    except Exception as e:
        structured_logger.error(
            message="Error invoking cloud run service",
            error=str(e),
            traceback=traceback.format_exc(),
            service="api_router",
        )
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
    # Handle OPTIONS request for CORS preflight FIRST!
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

    structured_logger.info(
        message="Request received",
        method=request.method,
        headers=dict(request.headers),
        url=request.url,
        args=dict(request.args),
        service="api_router",
    )

    auth_header = request.headers.get("Authorization")
    id_token = auth_header.split("Bearer ")[1].strip()
    auth = firebase_admin.auth.verify_id_token(id_token)
    uid = auth["uid"]

    try:
        body = request.get_json(silent=True)
        structured_logger.info(message="Request body", body=body, service="api_router")
    except Exception as e:
        structured_logger(
            message="Error parsing request body",
            error=str(e),
            level="ERROR",
            traceback=traceback.format_exc(),
        )

    try:
        # Get the request data
        request_data = request.get_json(silent=True)
        if not request_data:
            return https_fn.Response(
                status=900,
                response="Bad Request - No payload provided",
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Extract the target API and payload
        target_api = request_data.get("target_api")
        payload = request_data.get("payload")

        if not target_api:
            return https_fn.Response(
                status=901,
                response="Bad Request - No target API specified",
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Get project details from environment
        project_id = os.environ["PROJECT_ID"]
        region = os.environ["REGION"]
        environment = os.environ["ENVIRONMENT"]

        # Get authorization header and log diagnostics
        auth_header = request.headers.get("Authorization")
        structured_logger.info(
            function_level="Parent",
            message="Authorization header diagnostics",
            target_api=target_api,
            payload=payload,
            header_value=auth_header if auth_header else None,
            starts_with_bearer=(
                auth_header.startswith("Bearer ") if auth_header else False
            ),
            header_length=len(auth_header) if auth_header else 0,
            all_headers=dict(request.headers),
            service="api_router",
        )

        # Validate authorization header
        if not auth_header:
            structured_logger.error(
                function_level="Parent",
                message="Missing Authorization header",
                target_api=target_api,
                headers=dict(request.headers),
                service="api_router",
            )
            return https_fn.Response(
                status=902,
                response=json.dumps(
                    {
                        "error": "Unauthorized",
                        "message": "Missing Authorization header",
                        "diagnostics": {
                            "header_present": False,
                            "all_headers": dict(request.headers),
                        },
                    }
                ),
                headers={"Access-Control-Allow-Origin": "*"},
            )

        if not auth_header.startswith("Bearer "):
            structured_logger.error(
                function_level="Parent",
                message="Missing Authorization header",
                target_api=target_api,
                auth_header=auth_header,
                service="api_router",
            )
            return https_fn.Response(
                status=903,
                response=json.dumps(
                    {
                        "error": "Unauthorized",
                        "message": "Invalid Authorization header format",
                        "diagnostics": {
                            "header_present": True,
                            "starts_with_bearer": False,
                            "header_value": auth_header,
                            "expected_format": "Bearer <token>",
                        },
                    }
                ),
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Extract token and validate
        token = auth_header.split("Bearer ")[1].strip()
        if not token:
            return https_fn.Response(
                status=904,
                response=json.dumps(
                    {
                        "error": "Unauthorized",
                        "message": "Missing token in Authorization header",
                        "diagnostics": {
                            "header_present": True,
                            "starts_with_bearer": True,
                            "token_present": False,
                            "header_value": auth_header,
                        },
                    }
                ),
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Route to appropriate service
        if target_api == "token_refresh":
            function_name = f"projects/{project_id}/locations/{region}/functions/{environment}-token-refresh"
            return invoke_cloud_function(function_name, payload, auth_header)
        elif target_api == "strava_auth_initiate":
            function_name = f"projects/{project_id}/locations/{region}/functions/{environment}-strava-auth-initiate"
            return invoke_cloud_function(function_name, payload, auth_header)
        elif target_api == "data_run":
            payload["uid"] = uid
            service_name = f"projects/{project_id}/locations/{region}/services/{environment}-fitnessllm-dp"
            return invoke_cloud_run_job(service_name, payload)
        else:
            return https_fn.Response(
                status=905,
                response=f"Bad Request - Invalid target API: {target_api}",
                headers={"Access-Control-Allow-Origin": "*"},
            )

    except Exception as e:
        structured_logger.error(
            message="Error in api_router",
            error=str(e),
            level="ERROR",
            traceback=traceback.format_exc(),
            service="api_router",
        )
        return https_fn.Response(
            status=906,
            response=str(e),
            headers={"Access-Control-Allow-Origin": "*"},
        )
