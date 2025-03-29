"""API Interface for Strava."""
import json
from enum import EnumType
from functools import partial
from os import environ

from beartype import beartype
from google.cloud import bigquery
from stravalib import Client
from stravalib.model import Stream, SummaryActivity
from tqdm import tqdm

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource
from fitnessllm_dataplatform.infrastructure.RedisConnect import RedisConnect
from fitnessllm_dataplatform.services.api_interface import APIInterface
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import (
    StravaKeys,
    StravaStreams,
)
from fitnessllm_dataplatform.stream.strava.entities.queries import (
    create_get_latest_activity_date_query,
)
from fitnessllm_dataplatform.utils.cloud_utils import get_secret, write_json_to_storage
from fitnessllm_dataplatform.utils.logging_utils import logger
from fitnessllm_dataplatform.utils.task_utils import get_enum_values_from_list


class StravaAPIInterface(APIInterface):
    """API Interface for Strava."""

    redis: RedisConnect
    client: Client
    partial_get_strava_storage: partial

    # @beartype
    def __init__(self, infrastructure_names: EnumType, redis=None):
        """Initializes Strava API Interface."""
        super().__init__()
        self.data_source = FitnessLLMDataSource.STRAVA
        self.ENV = environ.get("ENV", "dev")
        self.redis = redis or RedisConnect()
        self.strava_client = Client()  # Initially set empty
        strava_secret_token = get_secret(environ["STRAVA_SECRET"])
        client_id, client_secret = (
            int(strava_secret_token["client_id"]),
            strava_secret_token["client_secret"],
        )
        self.write_strava_var_to_env(
            client_id=int(client_id), client_secret=client_secret
        )
        self.refresh_access_token_at_expiration(
            client_id=client_id, client_secret=client_secret
        )
        strava_access_token_dict = self.redis.read_redis(
            StravaKeys.STRAVA_ACCESS_TOKEN.value
        )
        self.set_strava_access_token(strava_access_token_dict)
        self.InfrastructureNames = infrastructure_names
        self.athlete_id = self.get_athlete_summary()
        self.bq_client = bigquery.Client()

    @beartype
    def get_strava_access_token(
        self,
        client_id: int,
        client_secret: str,
        authorization_code: str,
    ) -> dict:
        """Retrieve strava access token.

        Args:
            client_id: Client ID.
            client_secret: Client secret.
            authorization_code: Authorization code.

        Returns:
            dict: Access token.
        """
        return self.strava_client.exchange_code_for_token(
            client_id=client_id, client_secret=client_secret, code=authorization_code
        )

    @beartype
    def refresh_access_token_at_expiration(
        self, client_id: int, client_secret: str
    ) -> None:
        """Refreshes strava access token if it happens to be expired.

        TTL of the current token is retrieved. If it happens to not exist or is less than 0, a new token is retrieved.
        """
        strava_access_token_dict = self.redis.read_redis(
            StravaKeys.STRAVA_ACCESS_TOKEN.value
        )
        if not strava_access_token_dict:
            self.write_refreshed_access_token_to_redis(
                client_id=client_id, client_secret=client_secret
            )
            logger.info("Strava token not found in redis, writing new token")
        redis_ttl = self.redis.get_ttl(StravaKeys.STRAVA_ACCESS_TOKEN.value)
        if redis_ttl < 0:
            self.write_refreshed_access_token_to_redis(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=strava_access_token_dict["refresh_token"],
            )
            logger.info("Strava token expired, writing new token")
        else:
            logger.info("Strava token still valid")

    @staticmethod
    def write_strava_var_to_env(client_id: int, client_secret: str) -> None:
        """Writes strava secret token to environment."""
        logger.info("Writing strava secret token to environment")
        environ["STRAVA_CLIENT_ID"] = str(client_id)
        environ["STRAVA_CLIENT_SECRET"] = client_secret

    @beartype
    def write_refreshed_access_token_to_redis(
        self, client_id: int, client_secret: str, refresh_token: str | None = None
    ) -> None:
        """Writes retrieved strava access token to redis."""
        logger.info("Refreshing strava access token")
        strava_access_token = None
        if refresh_token:
            strava_access_token = self.strava_client.refresh_access_token(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
            )
        if environ.get("AUTHORIZATION_TOKEN"):
            strava_access_token = self.get_strava_access_token(
                client_id=client_id,
                client_secret=client_secret,
                code=environ["AUTHORIZATION_TOKEN"],
            )
        if not refresh_token and environ["AUTHORIZATION_TOKEN"]:
            raise KeyError("No refresh token or authorization token found")

        if strava_access_token:
            self.redis.write_redis(
                key=StravaKeys.STRAVA_ACCESS_TOKEN.value,
                value=strava_access_token,
                ttl=strava_access_token["expires_at"] - 60,
            )
        logger.info("Refreshed strava access token")

    @beartype
    def set_strava_access_token(self, strava_access_dict_from_redis: dict) -> None:
        """Instantiate strava client."""
        strava_access_token = (
            strava_access_dict_from_redis["access_token"]
            if strava_access_dict_from_redis
            else None
        )
        if not strava_access_token:
            logger.warning("Strava access token not found in redis")
            return None
        self.strava_client = Client(
            access_token=strava_access_token,
            refresh_token=strava_access_dict_from_redis.get("refresh_token"),
            token_expires=strava_access_dict_from_redis.get("expires_at"),
        )
        logger.info("Set strava access token")

    @beartype
    def get_athlete_summary(self) -> str:
        """Get athlete summary.

        The current athlete summary is retrieved based on the applied authorization token. The summary is saved to
        storage and the id is returned.
        """
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
        activity_dump = activity.model_dump()
        path = self.partial_get_strava_storage(
            strava_model=StravaStreams.ACTIVITY, activity_id=str(activity_dump["id"])
        )
        write_json_to_storage(path, json.loads(activity.model_dump_json()))
        return str(activity_dump["id"])

    @beartype
    def get_athlete_activity_streams(self, activity: SummaryActivity) -> None:
        """Get athlete stream.

        For a particular athlete's activity, the streams are retrieved and saved to storage.
        """
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
            write_json_to_storage(path, json.loads(stream_data.model_dump_json()))

    @beartype
    def get_all_activities(self) -> None:
        """Get all activities."""
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
