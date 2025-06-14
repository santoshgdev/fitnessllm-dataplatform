"""API Interface for Strava."""

import json
from enum import EnumType
from functools import partial
from os import environ

from beartype import beartype
from fitnessllm_shared.logger_utils import structured_logger
from google.cloud import bigquery
from stravalib import Client
from stravalib.model import Stream, SummaryActivity
from tqdm import tqdm
from utils.cloud_utils import wrapped_write_json_to_storage

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource
from fitnessllm_dataplatform.infrastructure.FirebaseConnect import FirebaseConnect
from fitnessllm_dataplatform.infrastructure.RedisConnect import RedisConnect
from fitnessllm_dataplatform.services.api_interface import APIInterface
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.stream.strava.entities.queries import (
    create_get_latest_activity_date_query,
)
from fitnessllm_dataplatform.utils.cloud_utils import get_secret, write_json_to_storage
from fitnessllm_dataplatform.utils.task_utils import get_enum_values_from_list


class StravaAPIInterface(APIInterface):
    """Handles the execution of ETL tasks for Strava data.

    This method processes SQL queries located in the specified directory,
    executes delete and insert operations on the target tables in the Silver
    layer, and logs the results of each operation. It ensures that data is
    properly transformed and loaded into the Silver layer.

    Raises:
        Exception: If any query execution fails or encounters an error.
    """

    redis: RedisConnect
    client: Client
    partial_get_strava_storage: partial
    service_name = "strava_ingest"

    # @beartype
    def __init__(
        self,
        uid: str,
        infrastructure_names: EnumType,
        access_token: str,
        firebase: FirebaseConnect,
    ):
        """Initializes the Strava API Interface.

        This constructor sets up the necessary attributes for interacting with the
        Strava API, including a unique identifier, infrastructure configuration,
        access token, and Firebase connection.

        Args:
            uid (str): A unique identifier for the API interface instance.
            infrastructure_names (EnumType): Infrastructure configuration details.
            access_token (str): The access token for authenticating with the Strava API.
            firebase (FirebaseConnect): Firebase connection instance for data storage and retrieval.
        """
        super().__init__()
        self.uid = uid
        self.strava_client = None
        self.data_source = FitnessLLMDataSource.STRAVA
        self.ENV = environ.get("ENV", "dev")
        self.firebase = firebase
        strava_secret_token = get_secret(environ["STRAVA_SECRET"])

        if (
            not strava_secret_token["client_id"]
            or not strava_secret_token["client_secret"]
        ):
            structured_logger.error(
                message="Strava client ID or secret token missing",
                **self._get_common_fields(),
            )
            raise Exception(
                "Client ID or Secret Token missing"
            )  # TODO: Perhaps implement a separate exception type?

        self.write_strava_var_to_env(
            client_id=int(strava_secret_token["client_id"]),
            client_secret=strava_secret_token["client_secret"],
        )
        self.set_strava_client(access_token)
        self.InfrastructureNames = infrastructure_names
        self.athlete_id = self.get_athlete_summary()
        self.bq_client = bigquery.Client()

    @beartype
    def _get_common_field(self) -> dict[str, str]:
        fields = super()._get_common_fields()
        fields.update({"athlete_id": self.athlete_id})
        return fields

    @beartype
    def write_strava_var_to_env(self, client_id: int, client_secret: str) -> None:
        """Writes Strava client ID and secret token to the environment variables.

        This method sets the `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` environment
        variables using the provided client ID and secret token. It also logs the operation
        for tracking purposes.

        Args:
            client_id (int): The client ID for the Strava API.
            client_secret (str): The client secret token for the Strava API.

        Returns:
            None
        """
        structured_logger.info(
            message="Writing strava secret token to environment",
            **self._get_common_fields(),
        )
        structured_logger.info(
            message="Writing strava secret token to environment",
            **self._get_common_fields(),
        )
        environ["STRAVA_CLIENT_ID"] = str(client_id)
        environ["STRAVA_CLIENT_SECRET"] = client_secret

    @beartype
    def set_strava_client(self, access_token: str) -> None:
        """Sets up the Strava client with the provided access token.

        This method initializes the Strava client using the given access token.
        If no access token is provided, it logs a warning and does not set up the client.

        Args:
            access_token (str): The access token for authenticating with the Strava API.

        Returns:
            None
        """
        if not access_token:
            structured_logger.warning(
                message="No strava access token provided", **self._get_common_fields()
            )
            structured_logger.warning(
                message="No strava access token provided", **self._get_common_fields()
            )
            return None
        self.strava_client = Client(access_token=access_token)
        structured_logger.info(
            message="Set strava access token", **self._get_common_fields()
        )
        return None

    @beartype
    def get_athlete_summary(self) -> str:
        """Retrieves and saves the athlete summary.

        This method fetches the current athlete summary using the Strava API based on the
        provided authorization token. The summary is saved to cloud storage, and the athlete's
        ID is returned.

        Returns:
            str: The ID of the athlete.

        Raises:
            Any exceptions raised by the Strava API client or storage utilities will propagate.
        """
        structured_logger.info(
            message="Getting athlete summary", **self._get_common_fields()
        )
        athlete = self.strava_client.get_athlete()

        self.partial_get_strava_storage = partial(
            get_strava_storage_path,
            bucket=self.InfrastructureNames.bronze_bucket,
            athlete_id=str(athlete.id),
        )
        write_json_to_storage(
            self.partial_get_strava_storage(
                strava_model=StravaStreams.ATHLETE_SUMMARY, activity_id=str(0)
            ),
            athlete.model_dump_json(),
        )
        return str(athlete.id)

    @beartype
    def get_activity_summary(self, activity: SummaryActivity) -> str:
        """Retrieves and saves the summary of a specific activity.

        This method processes the given activity by extracting its summary and saving it
        to cloud storage. The activity's ID is then returned for further reference.

        Args:
            activity (SummaryActivity): The activity object whose summary is to be retrieved.

        Returns:
            str: The ID of the processed activity.

        Raises:
            Any exceptions raised during the storage operation will propagate.
        """
        structured_logger.info(
            message="Getting activity summary", **self._get_common_fields()
        )
        activity_dump = activity.model_dump()
        path = self.partial_get_strava_storage(
            strava_model=StravaStreams.ACTIVITY, activity_id=str(activity_dump["id"])
        )
        wrapped_write_json_to_storage(
            uid=self.uid,
            data_source=self.data_source.value,
            path=path,
            data=json.loads(activity.model_dump_json()),
        )
        return str(activity_dump["id"])

    @beartype
    def get_athlete_activity_streams(self, activity: SummaryActivity) -> None:
        """Retrieve and save activity streams for a specific athlete's activity.

        This method fetches the streams associated with a given activity for an athlete
        using the Strava API. The retrieved streams are filtered to exclude certain types
        (e.g., "ACTIVITY" and "ATHLETE_SUMMARY") and are saved to cloud storage.

        Args:
            activity (SummaryActivity): The activity object for which streams are to be retrieved.

        Returns:
            None: This method does not return any value. It saves the retrieved streams to storage.

        Raises:
            Any exceptions raised by the Strava API client or storage utilities will propagate.
        """
        structured_logger.info(
            message="Getting athlete activity streams", **self._get_common_fields()
        )
        activity_id = self.get_activity_summary(activity)

        non_activity_streams = StravaStreams.filter_streams(
            exclude=["ACTIVITY", "ATHLETE_SUMMARY"]
        )
        streams = self.strava_client.get_activity_streams(
            activity_id=int(activity_id),
            types=get_enum_values_from_list(non_activity_streams),
        )
        for stream in non_activity_streams:
            stream_data = streams.get(stream.value, Stream())
            path = self.partial_get_strava_storage(
                strava_model=stream, activity_id=str(activity_id)
            )
            wrapped_write_json_to_storage(
                uid=self.uid,
                data_source=self.data_source.value,
                path=path,
                data=json.loads(stream_data.model_dump_json()),
            )

    @beartype
    def get_all_activities(self) -> None:
        """Retrieve and process all activities for the authenticated athlete.

        This method fetches all activities for the athlete from the Strava API,
        starting from the latest activity date stored in the database. For each
        activity, it retrieves and saves the associated activity streams.

        Returns:
            None: This method does not return any value. It processes and saves
            the activities and their streams to cloud storage.

        Raises:
            Any exceptions raised by the Strava API client, BigQuery client, or
            storage utilities will propagate.
        """
        structured_logger.info(
            message="Getting all activities", **self._get_common_fields()
        )
        latest_activity_date = (
            self.bq_client.query(
                create_get_latest_activity_date_query(
                    self.ENV, self.athlete_id, self.data_source
                )
            )
            .to_dataframe()
            .iloc[0, 0]
        )
        activities = list(self.strava_client.get_activities(after=latest_activity_date))
        for activity in tqdm(activities, desc="Getting activities"):
            self.get_athlete_activity_streams(activity)
