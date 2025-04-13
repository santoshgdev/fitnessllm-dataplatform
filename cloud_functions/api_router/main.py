"""Main Entry point for cloud function."""
import json
import os
from typing import Any, Dict, Tuple

import functions_framework
import requests
from firebase_functions import https_fn
from google.cloud import functions_v2, run_v2

from .utils.logger_utils import log_structured


def invoke_cloud_function(function_name: str, payload: Dict) -> Tuple[Any, int]:
    """Invoke a Cloud Function using HTTPS.

    Args:
        function_name: Full resource name of the function
        payload: The JSON payload to send

    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        # Get the function URL
        client = functions_v2.FunctionServiceClient()
        function = client.get_function(name=function_name)
        url = function.service_config.uri

        log_structured("Invoking cloud function", 
                      url=url,
                      payload=payload,
                      target_function=function_name.split('/')[-1])

        # For token refresh, we need to pass the data_source as a query parameter
        if 'data_source' in payload:
            url = f"{url}?data_source={payload['data_source']}"
            log_structured("Modified URL with query params", url=url)

        # Make the request
        response = requests.post(url, json=payload)
        
        # Log the response details
        log_structured("Received response",
                      status_code=response.status_code,
                      headers=dict(response.headers),
                      content=response.text)

        # Handle non-200 responses
        if response.status_code != 200:
            log_structured("Non-200 response received",
                          status_code=response.status_code,
                          response_text=response.text,
                          level="ERROR")
            return response.text, response.status_code

        # Try to parse JSON response
        try:
            if response.text:
                return response.json(), response.status_code
            return {"message": response.text}, response.status_code
        except json.JSONDecodeError as e:
            log_structured("Failed to parse JSON response",
                          error=str(e),
                          response_text=response.text,
                          level="ERROR")
            return "Invalid JSON response from function", 500

    except Exception as e:
        log_structured("Error invoking cloud function",
                      error=str(e),
                      level="ERROR")
        return str(e), 500


def invoke_cloud_run(service_name: str, payload: Dict) -> Tuple[Any, int]:
    """Invoke a Cloud Run service using HTTPS.

    Args:
        service_name: Full resource name of the service
        payload: The JSON payload to send

    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        # Get the service URL
        client = run_v2.ServicesClient()
        service = client.get_service(name=service_name)
        url = service.uri

        log_structured("Invoking cloud run service",
                      url=url,
                      payload=payload,
                      target_service=service_name.split('/')[-1])

        # Make the request
        response = requests.post(url, json=payload)

        # Log the response details
        log_structured("Received response",
                      status_code=response.status_code,
                      headers=dict(response.headers),
                      content=response.text)

        # Handle non-200 responses
        if response.status_code != 200:
            log_structured("Non-200 response received",
                          status_code=response.status_code,
                          response_text=response.text,
                          level="ERROR")
            return response.text, response.status_code

        # Try to parse JSON response
        try:
            if response.text:
                return response.json(), response.status_code
            return {"message": response.text}, response.status_code
        except json.JSONDecodeError as e:
            log_structured("Failed to parse JSON response",
                          error=str(e),
                          response_text=response.text,
                          level="ERROR")
            return "Invalid JSON response from service", 500

    except Exception as e:
        log_structured("Error invoking cloud run service",
                      error=str(e),
                      level="ERROR")
        return str(e), 500


@functions_framework.http
def api_router(request):
    """Cloud function that acts as an API router.

    Routes requests to different endpoints based on the payload.
    """
    # Log all request details at the start
    log_structured("Request received",
                  method=request.method,
                  headers=dict(request.headers),
                  url=request.url,
                  args=dict(request.args))

    try:
        body = request.get_json(silent=True)
        log_structured("Request body", body=body)
    except Exception as e:
        log_structured("Error parsing request body",
                      error=str(e),
                      level="ERROR")

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

        # Route to appropriate service
        if target_api == "token_refresh":
            function_name = f"projects/{project_id}/locations/{region}/functions/{environment}-token-refresh"
            response_data, status_code = invoke_cloud_function(function_name, payload)
        elif target_api == "data_run":
            service_name = f"projects/{project_id}/locations/{region}/services/{environment}-fitnessllm-dp"
            response_data, status_code = invoke_cloud_run(service_name, payload)
        else:
            return https_fn.Response(
                status=400,
                response=f"Bad Request - Invalid target API: {target_api}",
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # Return the response
        return https_fn.Response(
            status=status_code,
            response=json.dumps(response_data) if isinstance(response_data, dict) else response_data,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )

    except Exception as e:
        log_structured("Error in api_router",
                      error=str(e),
                      level="ERROR")
        return https_fn.Response(
            status=500,
            response=str(e),
            headers={"Access-Control-Allow-Origin": "*"},
        )
