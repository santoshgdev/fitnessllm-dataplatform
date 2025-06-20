"""Firebase connection module."""

import firebase_admin
from firebase_admin import firestore
from fitnessllm_shared.logger_utils import structured_logger


class FirebaseConnect:
    """Infrastructure Firebase."""

    def __init__(self, uid):
        """Init function."""
        self.uid = uid
        self.app = firebase_admin.initialize_app()
        self.open_connection()

    def open_connection(self):
        """Open Firebase connection."""
        self.interface = firestore.client()
        structured_logger.debug("Opened Firebase connection.", uid=self.uid)

    def close_connection(self):
        """Close Firebase connection."""

    def write(self, data):
        """Write data to Firebase."""

    def read_user(self):
        """Read user from Firebase."""
        return self.interface.collection("users").document(self.uid)
