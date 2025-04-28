"""Main entry point for Strava Auth Initiate."""
import json
import logging
import os
import time
import traceback

import firebase_admin
import functions_framework
import requests
from firebase_admin import firestore, initialize_app
from firebase_functions import https_fn, options

from .utils.cloud_utils import get_secret
from .utils.logger_utils import partial_log_structured
from .utils.task_utils import encrypt_token

# Initialize Firebase Admin with default credentials
try:
    initialize_app()
    partial_log_structured(message="Firebase Admin initialized successfully")
except Exception as e:
    partial_log_structured(
        message="Error initializing Firebase Admin",
        error=str(e),
        level="ERROR",
        traceback=traceback.format_exc(),
    )
    raise


@https_fn.on_request(
    cors=options.CorsOptions(cors_origins=["*"], cors_methods=["POST", "OPTIONS"])
)
@functions_framework.http
def strava_auth_initiate(request):
    """Handle CORS preflight and main request."""
    # Set CORS headers
    headers = {
        "Access-Control-Allow-Origin": "https://dev.fitnessllm.app",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
    }

    if request.method == "OPTIONS":
        return https_fn.Response(status=200, headers=headers)

    try:
        # Get Firebase ID token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return https_fn.Response(
                status=401, headers=headers, message="Unauthorized"
            )

        id_token = auth_header.split("Bearer ")[1]
        auth = firebase_admin.auth.verify_id_token(id_token)
        user_id = auth["uid"]

        data = request.get_json()
        authorization_code = data.get("authorizationCode")
        if not authorization_code:
            return https_fn.Response(
                status=401, headers=headers, error="Authorization code required"
            )

        # Retrieve secret
        secret_payload = json.loads(strava_secret.value)

        encryption_key = get_secret(os.environ["ENCRYPTION_SECRET"])["token"]

        # Exchange code with Strava
        response = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": int(secret_payload["client_id"]),
                "client_secret": secret_payload["client_secret"],
                "code": authorization_code,
                "grant_type": secret_payload["grant_type"],
            },
        )
        response.raise_for_status()
        strava_data = response.json()

        # Encrypt tokens
        access_token_enc = encrypt_token(strava_data["access_token"], encryption_key)
        refresh_token_enc = encrypt_token(strava_data["refresh_token"], encryption_key)

        # Prepare Firestore update
        db = firestore.client()
        user_ref = db.collection("users").document(user_id)
        now = firestore.SERVER_TIMESTAMP

        update_data = {
            "stream=strava": {
                "accessToken": access_token_enc,
                "refreshToken": refresh_token_enc,
                "expiresAt": strava_data.get("expires_at", int(time.time()) + 21600),
                "tokenType": strava_data.get("token_type", "Bearer"),
                "scope": strava_data.get("scope", "read,activity:read"),
                "athleteId": strava_data["athlete"]["id"],
                "athlete": {
                    "id": strava_data["athlete"]["id"],
                    "firstname": strava_data["athlete"].get("firstname", ""),
                    "lastname": strava_data["athlete"].get("lastname", ""),
                    "profile": strava_data["athlete"].get("profile", ""),
                },
                "lastUpdated": now,
                "lastTokenRefresh": now,
                "connectionStatus": "active",
                "version": "1.0",
            },
            "integrations.strava": {
                "connected": True,
                "athleteId": strava_data["athlete"]["id"],
                "lastUpdated": now,
                "connectionStatus": "active",
                "scope": strava_data.get("scope", "read,activity:read"),
            },
        }

        user_ref.update(update_data)
        return https_fn.Response(
            status=200,
            success=True,
            athleteId=strava_data["athlete"]["id"],
            scope=strava_data["scope"],
            headers=headers,
        )

    except Exception as e:
        logging.exception("Error in Strava auth")
        error_message = str(e)
        if isinstance(e, requests.HTTPError):
            error_message = f"Strava API error: {e.response.text}"
        return https_fn.Response(error_message, 401, headers)
