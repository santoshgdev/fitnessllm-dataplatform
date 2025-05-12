"""Conftest for cloud_functions."""

import random
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from faker import Faker

fake = Faker()


def generate_fake_strava_doc():
    """Generate a fake Strava document for testing."""
    user_id = str(uuid.uuid4()).replace("-", "")[:28]
    now = datetime.now(tz=timezone.utc)
    created_date = now - timedelta(days=random.randint(5, 30))
    connected_date = created_date + timedelta(days=random.randint(1, 4))
    first_name = fake.first_name()
    last_name = fake.last_name()
    athlete_id = random.randint(10000000, 99999999)

    strava_doc = {
        "accessToken": f"jtzp{fake.sha256()[:40]}==CZ1ltb{fake.sha256()[:40]}",
        "athlete": {
            "firstname": first_name,
            "id": athlete_id,
            "lastname": last_name[0],
            "profile": None,
        },
        "connected": True,
        "expiresAt": int((now + timedelta(days=90)).timestamp()),
        "firstConnected": datetime.fromtimestamp(
            connected_date.timestamp(), tz=timezone.utc
        ),
        "lastTokenRefresh": datetime.fromtimestamp(connected_date.timestamp()),
        "lastUpdated": datetime.fromtimestamp(connected_date.timestamp()),
        "refreshToken": f"X/{fake.sha256()[:40]}=={fake.sha256()[:60]}",
        "scope": "read,activity:read",
        "type": "strava",
        "uid": user_id,
        "version": "1.0",
        "created_time": datetime.fromtimestamp(created_date.timestamp()),
        "display_name": first_name,
        "email": fake.email(),
        "photo_url": f"https://lh3.googleusercontent.com/a/{fake.sha256()[:40]}=s96-c",
    }
    return user_id, strava_doc


@pytest.fixture
def test_user_data(firebase_emulator):
    """Fixture to create a test user with Strava data."""
    db = firebase_emulator
    user_id, strava_doc = generate_fake_strava_doc()
    db.collection("users").document(user_id).collection("stream").document(
        "strava"
    ).set(strava_doc)
    yield {"user_id": user_id, "db": db}
    db.collection("users").document(user_id).collection("stream").document(
        "strava"
    ).delete()
    db.collection("users").document(user_id).delete()
