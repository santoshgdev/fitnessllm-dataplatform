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
    """Handler for batch processing users.

    This class provides methods to process user data in batches, including
    retrieving user information, processing individual users, and handling
    data from various sources. It interacts with Firestore for data storage
    and retrieval and uses a startup handler for ETL operations.
    """

    def __init__(self) -> None:
        """Initializes the BatchHandler instance.

        This constructor sets up the Firestore client and the Startup handler
        required for batch processing operations.
        """
        self.db = firestore.Client()
        self.startup = Startup()

    @beartype
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieves all user documents from the Firestore "users" collection.

        This method queries the "users" collection in the Firestore database and
        returns a list of dictionaries, where each dictionary represents a user's data.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing user data.
        """
        users_ref = self.db.collection("users")
        users = users_ref.stream()
        return [user.to_dict() for user in users]

    @beartype
    def get_user_stream_data(
        self, uid: str, data_source: FitnessLLMDataSource
    ) -> Optional[dict[str, Any]]:
        """Retrieves stream data for a specific user and data source.

        This method fetches the stream data for a given user ID and data source
        from the Firestore database. If no data is found, it returns None.

        Args:
            uid (str): The unique identifier of the user.
            data_source (FitnessLLMDataSource): The data source for which the stream data is retrieved.

        Returns:
            Optional[dict[str, Any]]: A dictionary containing the user's stream data if found,
            otherwise None.
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
        """Processes a single user's data for a specified data source.

        This method retrieves the user's stream data, refreshes the data using the
        appropriate function from the refresh function mapping, and performs a full
        ETL (Extract, Transform, Load) process for the user. Logs are generated to
        track the progress and handle errors.

        Args:
            user_id (str): The unique identifier of the user in Firestore.
            data_source (FitnessLLMDataSource): The data source to process for the user.
                Defaults to FitnessLLMDataSource.STRAVA.

        Returns:
            None

        Raises:
            KeyError: If the refresh token is missing in the user's stream data.
            ValueError: If an invalid value is encountered during processing.
            firestore.exceptions.NotFound: If the user or stream data is not found in Firestore.
            Exception: For any other unexpected errors during processing.
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
        except (KeyError, ValueError, firestore.exceptions.NotFound) as e:
            structured_logger.error(
                message="Failed to process user",
                uid=user_id,
                exception=str(e),
                exception_type=type(e).__name__,
                data_source=data_source.value,
                service="batch_handler",
            )
            raise
        except Exception as e:
            structured_logger.error(
                message="Unexpected error while processing user",
                uid=user_id,
                exception=str(e),
                exception_type=type(e).__name__,
                data_source=data_source.value,
                service="batch_handler",
            )

    @beartype
    def process_all_users(
        self, data_source: FitnessLLMDataSource = FitnessLLMDataSource.STRAVA
    ) -> None:
        """Processes all users in the database for a specified data source.

        This method retrieves all user documents from the Firestore database,
        iterates through each user, and processes their data using the specified
        data source. Logs are generated to track the progress and handle any
        issues encountered during processing.

        Args:
            data_source (FitnessLLMDataSource): The data source to process for all users.
                Defaults to FitnessLLMDataSource.STRAVA.

        Returns:
            None
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
                    message="Skipping user without uid",
                    uid=user_id,
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
    try:
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
    finally:
        # Log completion before closing handlers
        structured_logger.info("Batch handler completed", service="batch_handler")
        # Ensure all logs are flushed and handlers are closed
        for handler in structured_logger.handlers:
            handler.flush()
            handler.close()
