import random
import uuid
from collections import defaultdict
from datetime import timedelta, datetime
from unittest.mock import MagicMock

class InMemoryFirestoreDoc:
    def __init__(self, data=None):
        self._data = data or {}
        self.exists = data is not None
        # Add subcollections support
        self._subcollections = defaultdict(InMemoryFirestoreCollection)

    def to_dict(self):
        return self._data.copy() if self._data else None

    def set(self, data):
        self._data = data
        self.exists = True

    def update(self, data):
        if not self.exists:
            raise Exception("Document does not exist")
        self._data.update(data)

    def get(self):
        """Mirrors Firestore's get() method by returning self."""
        return self

    def collection(self, subcollection_name):
        """Mirrors Firestore's collection() method on a document, returning a subcollection."""
        return self._subcollections[subcollection_name]

class InMemoryFirestoreCollection:
    def __init__(self):
        self._docs = {}

    def document(self, doc_id):
        if doc_id not in self._docs:
            self._docs[doc_id] = InMemoryFirestoreDoc()
        return self._docs[doc_id]

    def get_doc(self, doc_id):
        return self._docs.get(doc_id, InMemoryFirestoreDoc())

class InMemoryFirestoreClient:
    def __init__(self):
        self._collections = defaultdict(InMemoryFirestoreCollection)

    def collection(self, collection_name):
        return self._collections[collection_name]

    # For subcollections
    def get_subcollection(self, collection_name, doc_id, subcollection_name):
        doc = self.collection(collection_name).document(doc_id)
        if not hasattr(doc, '_subcollections'):
            doc._subcollections = defaultdict(InMemoryFirestoreCollection)
        return doc._subcollections[subcollection_name]


def populate_inmemory_firestore_with_users_and_streams(
    db=None,
    num_users=1,
    user_data_fn=None,
    streams_data_fn=None
):
    """
    Populates the in-memory Firestore with multiple users and their stream subcollections.
    - db: InMemoryFirestoreClient instance (optional, will create if not provided)
    - num_users: number of users to generate
    - user_data_fn: function(user_id, idx) -> dict for user doc (optional)
    - streams_data_fn: function(user_id, idx) -> dict of {stream_name: stream_doc} (optional)
    Returns (db, user_ids)
    """
    if db is None:
        db = InMemoryFirestoreClient()

    user_ids = []
    for idx in range(num_users):
        user_id = str(uuid.uuid4()).replace('-', '')[:28]
        user_ids.append(user_id)

        # Generate user data
        if user_data_fn:
            user_data = user_data_fn(user_id, idx)
        else:
            user_data = {
                "created_time": datetime.now(),
                "display_name": f"Test User {idx+1}",
                "email": f"test{idx+1}@example.com",
                "photo_url": f"https://example.com/photo{idx+1}.jpg",
                "uid": user_id,
            }

        # Generate streams data
        if streams_data_fn:
            streams_data = streams_data_fn(user_id, idx)
        else:
            now = datetime.now()
            strava_data = {
                "accessToken": f"fake_access_token_{idx+1}",
                "athlete": {
                    "firstname": f"Test{idx+1}",
                    "id": random.randint(10000000, 99999999),
                    "lastname": f"User{idx+1}",
                    "profile": None,
                    "connected": True,
                },
                "expiresAt": int((now + timedelta(days=90)).timestamp()),
                "firstConnected": now,
                "lastTokenRefresh": now,
                "lastUpdated": now,
                "refreshToken": f"fake_refresh_token_{idx+1}",
                "scope": "read,activity:read",
                "type": "strava",
                "uid": user_id,
                "version": "1.0",
            }
            streams_data = {"strava": strava_data}

        # Set user doc
        db.collection("users").document(user_id).set(user_data)

        # Set each stream doc in the subcollection
        for stream_name, stream_doc in streams_data.items():
            db.get_subcollection("users", user_id, "stream").document(stream_name).set(stream_doc)

    return db, user_ids