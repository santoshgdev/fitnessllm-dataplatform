"""Batch handler for processing all users."""
from typing import Optional

from beartype import beartype
from beartype.typing import Any, Dict, List
from entities.enums import FitnessLLMDataSource
from fitnessllm_shared.streams.strava import strava_refresh_oauth_token
from google.cloud import firestore
from google.cloud.firestore_v1 import DocumentReference

from fitnessllm_dataplatform.task_handler import Startup
from fitnessllm_dataplatform.utils.logging_utils import logger


class BatchHandler:
    """Handler for batch processing users."""

    def __init__(self) -> None:
        """Initialize the batch handler."""
        self.db = firestore.Client()
        self.startup = Startup()

    @beartype
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from Firestore.

        Returns:
            List of user documents.
        """
        users_ref = self.db.collection("users")
        users = users_ref.stream()
        return [user.to_dict() for user in users]

    @beartype
    def get_specific_user(self, user_id: str) -> Optional[DocumentReference]:
        """Get a specific user from Firestore.

        Args:
            user_id: User ID from Firestore.

        Returns:
            User document.
        """
        user_ref = self.db.collection("users").document(user_id)
        if user_ref.get().exists:
            return user_ref
        else:
            logger.warning(f"User {user_id} not found in Firestore.")
            return None

    @beartype
    def refresh_tokens(self, user_id: str, data_source: str) -> None:
        """Refresh tokens for a user.

        Args:
            user_id: User ID from Firestore.
            data_source: Data source to refresh tokens for.
        """
        user_ref = self.get_specific_user(user_id)

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_refresh_token = (
                user_ref.collection("stream")
                .document(data_source.lower())
                .get()
                .to_dict()
                .get("refreshToken")
            )
            assert strava_refresh_token
            strava_refresh_oauth_token(
                db=self.db, uid=user_id, refresh_token=strava_refresh_token
            )

    @beartype
    def process_user(
        self, user_id: str, data_source: str = FitnessLLMDataSource.STRAVA.value
    ) -> None:
        """Process a single user.

        Args:
            user_id: User ID from Firestore.
            data_source: Data source to process (default: strava).
        """
        self.refresh_tokens(user_id, data_source)
        try:
            logger.info(f"Processing user {user_id} for data source {data_source}")
            self.startup.full_etl(uid=user_id, data_source=data_source)
            logger.info(f"Successfully processed user {user_id}")
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {str(e)}")
            raise

    @beartype
    def process_all_users(
        self, data_source: str = FitnessLLMDataSource.STRAVA.value
    ) -> None:
        """Process all users in the database.

        Args:
            data_source: Data source to process (default: strava).
        """
        users = self.get_all_users()
        logger.info(f"Found {len(users)} users to process")
        # TODO: Need to add that if nothing is given to datasource, that for each user we run for all their datasources.
        for user in users:
            user_id = user.get("uid")
            if not user_id:
                logger.warning(f"Skipping user without uid: {user}")
                continue

            try:
                self.process_user(user_id, data_source)
            except Exception as e:
                logger.error(f"Failed to process user {user_id}: {str(e)}")
                # Continue with next user even if one fails
                continue

        logger.info("Finished processing all users")


if __name__ == "__main__":
    handler = BatchHandler()
    handler.process_all_users()
