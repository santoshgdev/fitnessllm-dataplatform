"""Batch handler for processing all users."""

from beartype import beartype
from beartype.typing import Any, Dict, List
from google.cloud import firestore

from fitnessllm_dataplatform.task_handler import Startup
from fitnessllm_dataplatform.utils.logging_utils import structured_logger


class BatchHandler:
    """Handler for batch processing users."""

    def __init__(self) -> None:
        """Initialize the batch handler."""
        self.db = firestore.Client()
        self.startup = Startup()

    @beartype
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieves all user documents from the Firestore "users" collection.

        Returns:
            A list of dictionaries representing each user's data.
        """
        users_ref = self.db.collection("users")
        users = users_ref.stream()
        return [user.to_dict() for user in users]

    @beartype
    def process_user(self, user_id: str, data_source: str = "strava") -> None:
        """Process a single user.

        Args:
            user_id: User ID from Firestore.
            data_source: Data source to process (default: strava).
        """
        try:
            structured_logger.info(
                message="Processing user", uid=user_id, data_source=data_source
            )
            self.startup.full_etl(uid=user_id, data_source=data_source)
            structured_logger.info(
                message="Successfully processed user",
                uid=user_id,
                data_source=data_source,
            )
        except Exception as e:
            structured_logger.error(
                message="Failed to process user", uid=user_id, exception=e
            )
            raise

    @beartype
    def process_all_users(self, data_source: str = "strava") -> None:
        """Process all users in the database.

        Args:
            data_source: Data source to process (default: strava).
        """
        users = self.get_all_users()
        structured_logger.info(
            message=f"Found {len(users)} users to process",
            data_source=data_source,
            batch=True,
            uid="all",
        )
        # TODO: Need to add that if nothing is given to datasource, that for each user we run for all their datasources.
        for user in users:
            user_id = user.get("uid")
            if not user_id:
                structured_logger.warning(
                    message=f"Skipping user without uid: {user}",
                    uid=user_id,
                    exception=user,
                )
                continue

            try:
                self.process_user(user_id, data_source)
            except Exception as e:
                structured_logger.error(
                    message="Failed to process user",
                    uid=user_id,
                    exception=e,
                    data_source=data_source,
                )
                # Continue with next user even if one fails
                continue
        structured_logger.info(
            message="Finished processing all users",
            data_source=data_source,
            batch=True,
            uid="all",
        )


if __name__ == "__main__":
    structured_logger.info("Starting batch handler")
    handler = BatchHandler()
    handler.process_all_users()
