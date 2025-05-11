"""Batch handler for processing all users."""

from os import environ
from typing import Optional

from beartype import beartype
from beartype.typing import Any, Dict, List
from entities.enums import FitnessLLMDataSource
from entities.mapping import REFRESH_FUNCTION_MAPPING
from fitnessllm_shared.logger_utils import structured_logger
from google.cloud import firestore

from fitnessllm_dataplatform.task_handler import Startup


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
    def get_user_stream_data(
        self, uid: str, data_source: FitnessLLMDataSource
    ) -> Optional[dict[str, Any]]:
        """Retrieves all user documents from the Firestore "users" collection.

        Returns:
            A list of dictionaries representing each user's data.
        """
        user_stream = (
            self.db.collection("users")
            .document(uid)
            .collection("stream")
            .document(data_source.value.lower())
        )
        return user_stream.get().to_dict()

    @beartype
    def process_user(
        self,
        user_id: str,
        data_source: FitnessLLMDataSource = FitnessLLMDataSource.STRAVA,
    ) -> None:
        """Process a single user.

        Args:
            user_id: User ID from Firestore.
            data_source: Data source to process (default: strava).
        """
        try:
            structured_logger.info(
                message="Processing user",
                uid=user_id,
                data_source=data_source.value,
                service="batch_handler",
            )
            refresh_function = REFRESH_FUNCTION_MAPPING[data_source.value]
            strava_data = self.get_user_stream_data(
                uid=user_id, data_source=data_source
            )
            refresh_function(self.db, user_id, strava_data["refreshToken"])

            self.startup.full_etl(uid=user_id, data_source=data_source.value)
            structured_logger.info(
                message="Successfully processed user",
                uid=user_id,
                data_source=data_source.value,
                service="batch_handler",
            )
        except Exception as e:
            structured_logger.error(
                message="Failed to process user",
                uid=user_id,
                exception=str(e),
                data_source=data_source.value,
                service="batch_handler",
            )
            raise

    @beartype
    def process_all_users(
        self, data_source: FitnessLLMDataSource = FitnessLLMDataSource.STRAVA
    ) -> None:
        """Process all users in the database.

        Args:
            data_source: Data source to process (default: strava).
        """
        users = self.get_all_users()
        structured_logger.info(
            message="Found users to process",
            user_count=len(users),
            data_source=data_source.value,
            batch=True,
            uid="all",
            service="batch_handler",
        )
        # TODO: Need to add that if nothing is given to datasource, that for each user we run for all their datasources.
        for user in users:
            user_id = user.get("uid")
            if not user_id:
                structured_logger.warning(
                    message=f"Skipping user without uid: {user}",
                    uid=user_id,
                    exception=user,
                    service="batch_handler",
                )
                continue

            self.process_user(user_id, data_source)
        structured_logger.info(
            message="Finished processing all users",
            data_source=data_source.value,
            batch=True,
            uid="all",
            service="batch_handler",
        )


if __name__ == "__main__":
    structured_logger.info("Starting batch handler", service="batch_handler")
    # TODO: Possibly reduce the number of environment variables.
    structured_logger.info(
        "Cloud run job name",
        CLOUD_RUN_JOB=environ["CLOUD_RUN_JOB"],
        CLOUD_RUN_EXECUTION_ID=environ["CLOUD_RUN_EXECUTION"],
        CLOUD_RUN_TASK_INDEX=environ["CLOUD_RUN_TASK_INDEX"],
        CLOUD_RUN_TASK_ATTEMPT=environ["CLOUD_RUN_TASK_ATTEMPT"],
        CLOUD_RUN_TASK_COUNT=environ["CLOUD_RUN_TASK_COUNT"],
    )
    handler = BatchHandler()
    handler.process_all_users()
