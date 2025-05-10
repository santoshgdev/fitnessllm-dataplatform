"""Utilities for testing Firestore interactions in memory."""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional


class InMemoryFirestoreDoc:
    """A class that simulates a Firestore document in memory.

    Attributes:
        _data (dict): The data stored in the document.
        exists (bool): Indicates whether the document exists.
        _subcollections (defaultdict): A dictionary of subcollections,
            where each subcollection is an instance of InMemoryFirestoreCollection.
    """

    def __init__(self, data=None):
        """Initializes an in-memory Firestore document.

        Args:
            data (dict, optional): The initial data for the document. Defaults to None.
        """
        self._data = data or {}
        self.exists = data is not None
        # Add subcollections support
        self._subcollections = defaultdict(InMemoryFirestoreCollection)

    def to_dict(self):
        """Converts the document's data to a dictionary.

        Returns:
            dict: A copy of the document's data, or None if no data exists.
        """
        return self._data.copy() if self._data else None

    def set(self, data):
        """Sets the document's data, overwriting any existing data.

        Args:
            data (dict): The new data to set in the document.
        """
        self._data = data
        self.exists = True

    def update(self, data):
        """Updates the document's data with the provided data.

        Args:
            data (dict): The data to update in the document.

        Raises:
            Exception: If the document does not exist.
        """
        if not self.exists:
            raise Exception("Document does not exist")
        self._data.update(data)

    def get(self):
        """Returns the current document instance.

        This method mirrors Firestore's `get()` method.

        Returns:
            InMemoryFirestoreDoc: The current document instance.
        """
        return self

    def collection(self, subcollection_name):
        """Retrieves a subcollection of the document.

        Args:
            subcollection_name (str): The name of the subcollection.

        Returns:
            InMemoryFirestoreCollection: The subcollection instance.
        """
        return self._subcollections[subcollection_name]


class InMemoryFirestoreCollection:
    """A class that simulates a Firestore collection in memory.

    Attributes:
        _docs (dict): A dictionary to store documents in the collection,
            where keys are document IDs and values are InMemoryFirestoreDoc instances.
    """

    def __init__(self):
        """Initializes an in-memory Firestore collection."""
        self._docs = {}

    def document(self, doc_id):
        """Retrieves a document from the collection by its ID.

        If the document does not exist,  it creates a new one and adds it to the collection.

        Args:
            doc_id (str): The ID of the document to retrieve or create.

        Returns:
            InMemoryFirestoreDoc: The document instance.
        """
        if doc_id not in self._docs:
            self._docs[doc_id] = InMemoryFirestoreDoc()
        return self._docs[doc_id]

    def get_doc(self, doc_id):
        """Retrieves a document from the collection by its ID.

        If the document does not exist, it returns a new instance of InMemoryFirestoreDoc.

        Args:
            doc_id (str): The ID of the document to retrieve.

        Returns:
            InMemoryFirestoreDoc: The document instance, or a new instance if the document does not exist.
        """
        return self._docs.get(doc_id, InMemoryFirestoreDoc())


class InMemoryFirestoreClient:
    """A class that simulates a Firestore client in memory.

    Attributes:
        _collections (defaultdict): A dictionary of collections, where each collection
            is an instance of InMemoryFirestoreCollection.
    """

    def __init__(self):
        """Initializes an in-memory Firestore client."""
        self._collections = defaultdict(InMemoryFirestoreCollection)

    def collection(self, collection_name: str) -> InMemoryFirestoreCollection:
        """Retrieves a collection by its name. If the collection does not exist, it creates a new one.

        Args:
            collection_name (str): The name of the collection to retrieve or create.

        Returns:
            InMemoryFirestoreCollection: The collection instance.
        """
        return self._collections[collection_name]

    def get_subcollection(
        self, collection_name: str, doc_id: str, subcollection_name: str
    ) -> InMemoryFirestoreCollection:
        """Retrieves a subcollection of a document within a collection.

        If the subcollection does not exist, it creates a new one.

        Args:
            collection_name (str): The name of the parent collection.
            doc_id (str): The ID of the document containing the subcollection.
            subcollection_name (str): The name of the subcollection to retrieve or create.

        Returns:
            InMemoryFirestoreCollection: The subcollection instance.
        """
        doc = self.collection(collection_name).document(doc_id)
        return doc._subcollections[subcollection_name]


def populate_inmemory_firestore_with_users_and_streams(
    db: Optional[InMemoryFirestoreClient] = None,
    num_users: int = 1,
):
    """Populates the in-memory Firestore with multiple users and their stream subcollections.

    Args:
        db: InMemoryFirestoreClient instance (optional, will create if not provided)
        num_users: number of users to generate

    Returns:
        A tuple containing (db, user_ids) where db is the InMemoryFirestoreClient
        and user_ids is a list of generated user IDs.
    """
    if db is None:
        db = InMemoryFirestoreClient()

    user_ids = []
    for idx in range(num_users):
        user_id = str(uuid.uuid4()).replace("-", "")[:28]
        user_ids.append(user_id)

        now = datetime.now(timezone.utc)

        user_data = {
            "created_time": now,
            "display_name": f"Test User {idx+1}",
            "email": f"test{idx+1}@example.com",
            "photo_url": f"https://example.com/photo{idx+1}.jpg",
            "uid": user_id,
        }

        strava_data = {
            "accessToken": f"fake_access_token_{idx+1}",
            "athlete": {
                "firstname": f"Test{idx+1}",
                "id": int(uuid.uuid4().int % (99999999 - 10000000) + 10000000),
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
            db.get_subcollection("users", user_id, "stream").document(stream_name).set(
                stream_doc,
            )

    return db, user_ids
