"""Main entry point for Strava Auth Initiate."""
import json
import logging
import os
import traceback

import firebase_admin
import functions_framework
import requests
from firebase_admin import firestore, initialize_app
from firebase_functions import https_fn, options
from fitnessllm_shared.cloud_utils import get_secret
from fitnessllm_shared.logger_utils import create_structured_logger
from fitnessllm_shared.task_utils import encrypt_token
from stravalib import Client

from .entities.constants import CORS_HEADERS

structured_logger = create_structured_logger(__name__)

try:
    initialize_app()
    structured_logger(message="Firebase Admin initialized successfully")
except Exception as e:
    structured_logger(
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
    """Handles Strava OAuth initiation, exchanges authorization code for tokens, encrypts and stores them in Firestore, and manages CORS and authentication for incoming requests.

    For POST requests, verifies the Firebase ID token, exchanges the Strava authorization code for access and refresh tokens, retrieves athlete profile data, encrypts sensitive tokens, and updates the user's Firestore document with connection details. Handles CORS preflight (OPTIONS) and returns appropriate error responses for authentication or API failures.
    """
    # Set CORS headers
    if request.method == "OPTIONS":
        return https_fn.Response(status=200, headers=CORS_HEADERS)

    try:
        # Get Firebase ID token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return https_fn.Response(
                status=401,
                headers=CORS_HEADERS,
                response=json.dumps(
                    {
                        "error": "Unauthorized",
                        "message": "Invalid Authorization header format",
                    }
                ),
            )

        # Extract the token from the Authorization header
        id_token = auth_header.split("Bearer ")[1].strip()
        if not id_token:
            return https_fn.Response(
                status=401,
                headers=CORS_HEADERS,
                response=json.dumps(
                    {
                        "error": "Unauthorized",
                        "message": "Missing token in Authorization header",
                    }
                ),
            )

        auth = firebase_admin.auth.verify_id_token(id_token)
        user_id = auth["uid"]

        data = request.get_json()
        authorization_code = data.get("code")
        if not authorization_code:
            return https_fn.Response(
                status=401,
                headers=CORS_HEADERS,
                response=json.dumps(
                    {"error": "Unauthorized", "message": "Authorization code required"},
                ),
            )

        # Retrieve secret
        strava_keys = get_secret(os.environ["STRAVA_SECRET"])

        encryption_key = get_secret(os.environ["ENCRYPTION_SECRET"])["token"]

        # Exchange code with Strava
        client = Client()
        token_response = client.exchange_code_for_token(
            client_id=int(strava_keys["client_id"]),
            client_secret=strava_keys["client_secret"],
            code=authorization_code,
        )
        access_token = token_response["access_token"]
        refresh_token = token_response["refresh_token"]
        expires_at = token_response["expires_at"]
        scope = token_response.get("scope", "read,activity:read")

        client = Client(access_token=access_token)
        athlete = client.get_athlete()

        # Athlete details
        athlete_id = athlete.id
        firstname = athlete.firstname
        lastname = athlete.lastname
        profile = athlete.profile_original

        # Encrypt tokens
        access_token_enc = encrypt_token(access_token, encryption_key)
        refresh_token_enc = encrypt_token(refresh_token, encryption_key)

        # Prepare Firestore update
        db = firestore.client()
        user_ref = db.collection("users").document(user_id)
        now = firestore.SERVER_TIMESTAMP

        stream_ref = user_ref.collection("stream")

        # Reference the 'strava' subcollection within 'stream'
        strava_ref = stream_ref.document("strava")

        # Prepare the data for the 'strava' document
        strava_data = {
            "uid": user_id,
            "type": "strava",
            "accessToken": access_token_enc,
            "refreshToken": refresh_token_enc,
            "expiresAt": expires_at,
            "scope": scope,
            "athlete": {
                "id": athlete_id,
                "firstname": firstname,
                "lastname": lastname,
                "profile": profile,
            },
            "firstConnected": now,
            "lastUpdated": now,
            "lastTokenRefresh": now,
            "connected": True,
            "version": "1.0",
        }

        strava_ref.set(strava_data, merge=True)
        return https_fn.Response(
            status=200,
            headers=CORS_HEADERS,
            response=json.dumps(
                {"message": "Strava connection successful", "athlete": athlete_id}
            ),
        )

    except Exception as e:
        logging.exception("Error in Strava auth")
        error_message = str(e)
        if isinstance(e, requests.HTTPError):
            error_message = f"Strava API error: {e.response.text}"
        return https_fn.Response(error_message, 401, CORS_HEADERS)
