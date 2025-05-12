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
    """API Interface for Strava."""

    SERVICE_NAME = "ingest"
    redis: RedisConnect
    client: Client
    partial_get_strava_storage: partial

    # @beartype
    def __init__(
        self,
        uid: str,
        infrastructure_names: EnumType,
        access_token: str,
        firebase: FirebaseConnect,
    ):
        """Initializes Strava API Interface."""
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
                uid=self.uid,
                data_source=self.data_source.value,
                service=self.SERVICE_NAME,
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
    def write_strava_var_to_env(self, client_id: int, client_secret: str) -> None:
        """Writes strava secret token to environment."""
        structured_logger.info(
            message="Writing strava secret token to environment",
            uid=self.uid,
            data_source=self.data_source.value,
        )
        structured_logger.info(
            message="Writing strava secret token to environment",
            service=self.SERVICE_NAME,
        )
        environ["STRAVA_CLIENT_ID"] = str(client_id)
        environ["STRAVA_CLIENT_SECRET"] = client_secret

    @beartype
    def set_strava_client(self, access_token: str) -> None:
        """Instantiate strava client."""
        if not access_token:
            structured_logger.warning(
                message="No strava access token provided",
                uid=self.uid,
                data_source=self.data_source.value,
            )
            structured_logger.warning(
                message="No strava access token provided",
                uid=self.uid,
                data_source=self.data_source,
                service=self.SERVICE_NAME,
            )
            return None
        self.strava_client = Client(access_token=access_token)
        structured_logger.info(
            message="Set strava access token",
            uid=self.uid,
            data_source=self.data_source.value,
        )
        return None

    @beartype
    def get_athlete_summary(self) -> str:
        """Get athlete summary.

        The current athlete summary is retrieved based on the applied authorization token. The summary is saved to
        storage and the id is returned.
        """
        structured_logger.info(
            message="Getting athlete summary",
            uid=self.uid,
            data_source=self.data_source.value,
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
        """Get activity summary.

        For a particular athlete's activity, the summary is retrieved and saved to storage. The id is returned.
        """
        structured_logger.info(
            message="Getting activity summary",
            uid=self.uid,
            data_source=self.data_source.value,
            service=self.SERVICE_NAME,
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
            message="Getting athlete activity streams",
            uid=self.uid,
            data_source=self.data_source.value,
            service=self.SERVICE_NAME,
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
                path, json.loads(stream_data.model_dump_json())
            )

    @beartype
    def get_all_activities(self) -> None:
        """Retrieve and process all activities for the authenticated athlete.

        This method fetches all activities for the athlete from the Strava API,
        starting from the latest activity date stored in the database. For each
        activity, it retrieves and saves the associated activity streams.

        Args:
            None

        Returns:
            None: This method does not return any value. It processes and saves
            the activities and their streams to cloud storage.

        Raises:
            Any exceptions raised by the Strava API client, BigQuery client, or
            storage utilities will propagate.
        """
        structured_logger.info(
            message="Getting all activities",
            uid=self.uid,
            data_source=self.data_source.value,
            service=self.SERVICE_NAME,
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
