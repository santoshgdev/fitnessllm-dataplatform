# conftest.py
import pytest
import firebase_admin
from firebase_admin import credentials, firestore, get_app, delete_app
from google.cloud.firestore import Client
import os
from datetime import datetime, timedelta
from faker import Faker
import random
import uuid
from unittest.mock import patch

# Initialize Faker
fake = Faker()

@pytest.fixture(scope="session")
def firebase_emulator():
    """Setup Firebase emulator connection"""
    os.environ["FIRESTORE_EMULATOR_HOST"] = "firebase-emulator:8080"
    os.environ["GCLOUD_PROJECT"] = "test-project"
    
    # Clean up any existing apps
    try:
        delete_app(get_app())
    except ValueError:
        pass
        
    # Mock the credentials loading
    with patch('google.auth.default') as mock_auth:
        mock_auth.return_value = (None, 'test-project')
        
        # Initialize with emulator configuration
        app = firebase_admin.initialize_app(options={
            'projectId': 'test-project',
            'databaseURL': 'http://localhost:8080'
        })
        try:
            yield firestore.client()
        finally:
            try:
                firebase_admin.delete_app(app)
            except ValueError:
                pass


def generate_fake_strava_doc():
    user_id = str(uuid.uuid4()).replace('-', '')[:28]
    now = datetime.now()
    created_date = now - timedelta(days=random.randint(5, 30))
    connected_date = created_date + timedelta(days=random.randint(1, 4))
    first_name = fake.first_name()
    last_name = fake.last_name()
    athlete_id = random.randint(10000000, 99999999)

    strava_doc = {
        'accessToken': f"jtzp{fake.sha256()[:40]}==CZ1ltb{fake.sha256()[:40]}",
        'athlete': {
            'firstname': first_name,
            'id': athlete_id,
            'lastname': last_name[0],
            'profile': None
        },
        'connected': True,
        'expiresAt': int((now + timedelta(days=90)).timestamp()),
        'firstConnected': datetime.fromtimestamp(connected_date.timestamp()),
        'lastTokenRefresh': datetime.fromtimestamp(connected_date.timestamp()),
        'lastUpdated': datetime.fromtimestamp(connected_date.timestamp()),
        'refreshToken': f"X/{fake.sha256()[:40]}=={fake.sha256()[:60]}",
        'scope': "read,activity:read",
        'type': "strava",
        'uid': user_id,
        'version': "1.0",
        'created_time': datetime.fromtimestamp(created_date.timestamp()),
        'display_name': first_name,
        'email': fake.email(),
        'photo_url': f"https://lh3.googleusercontent.com/a/{fake.sha256()[:40]}=s96-c",
    }
    return user_id, strava_doc

@pytest.fixture
def test_user_data(firebase_emulator):
    db = firebase_emulator
    user_id, strava_doc = generate_fake_strava_doc()
    db.collection('users').document(user_id).collection('stream').document('strava').set(strava_doc)
    yield {"user_id": user_id, "db": db}
    db.collection('users').document(user_id).delete()
