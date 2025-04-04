"""Firebase connection module."""
import firebase_admin
from firebase_admin import firestore

from fitnessllm_dataplatform.utils.logging_utils import logger


class FirebaseConnect:
    """Infrastructure Firebase."""

    def __init__(self, uid):
        """Init function."""
        self.app = firebase_admin.initialize_app()
        self.open_connection()
        self.uid = uid

    def open_connection(self):
        """Open Firebase connection."""
        self.interface = firestore.client()
        logger.debug("Opened Firebase connection.")

    def close_connection(self):
        """Close Firebase connection."""
        pass

    def write(self, data):
        """Write data to Firebase."""
        pass

    def read_user(self):
        """Read user from Firebase."""
        return self.interface.collection("users").document(self.uid)
