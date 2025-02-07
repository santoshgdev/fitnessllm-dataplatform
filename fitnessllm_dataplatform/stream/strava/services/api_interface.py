"""API Interface for Strava."""
import json
from enum import EnumType
from functools import partial
from os import environ

import requests
from beartype import beartype
from google.cloud import bigquery
from stravalib import Client
from stravalib.model import Stream, SummaryActivity
from tqdm import tqdm

from fitnessllm_dataplatform.infrastructure.RedisConnect import RedisConnect
from fitnessllm_dataplatform.services.api_interface import APIInterface
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import (
    StravaKeys,
    StravaStreams,
    StravaURLs,
)
from fitnessllm_dataplatform.stream.strava.entities.queries import (
    create_get_latest_activity_date_query,
)
from fitnessllm_dataplatform.utils.cloud_utils import get_secret, write_json_to_storage
from fitnessllm_dataplatform.utils.logging_utils import logger
from fitnessllm_dataplatform.utils.request_utils import handle_status_code
from fitnessllm_dataplatform.utils.task_utils import get_enum_values_from_list


class StravaAPIInterface(APIInterface):
    """API Interface for Strava."""

    redis: RedisConnect
    client: Client
    partial_get_strava_storage: partial

    # @beartype
    def __init__(self, infrastructure_names: EnumType, redis=None):
        super().__init__()
        self.redis = redis or RedisConnect()
        self.refresh_access_token_at_expiration()
        strava_access_token_dict = self.redis.read_redis(
            StravaKeys.STRAVA_ACCESS_TOKEN.value
        )
        self.instantiate_strava_lib(strava_access_token_dict)
        self.InfrastructureNames = infrastructure_names
        self.athlete_id = self.get_athlete_summary()
        self.client = bigquery.Client()

    @beartype
    @staticmethod
    def get_strava_access_token(
        client_id: str,
        client_secret: str,
        code: str,
        grant_type: str = "authorization_code",
    ) -> dict:
        """Retrieve strava access token.

        Args:
            client_id: Client ID.
            client_secret: Client secret.
            code: Authorization code.
            grant_type: Grant type.

        Returns:
            dict: Access token.
        """
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": grant_type,
        }
        response = requests.post(StravaURLs.AUTH_URL.value, data=payload)
        if response.status_code != 200:
            raise Exception(
                f"Request to strava failed with status {response.status_code}: {response.text}"
            )
        return handle_status_code(response)

    @beartype
    def refresh_access_token_at_expiration(self) -> None:
        """Refreshes strava access token if it happens to be expired.

        TTL of the current token is retrieved. If it happens to not exist or is less than 0, a new token is retrieved.
        """
        redis_ttl = self.redis.get_ttl(StravaKeys.STRAVA_ACCESS_TOKEN.value)
        if redis_ttl is None or redis_ttl < 0:
            self.write_refreshed_access_token_to_redis()
        else:
            logger.info("Strava token still valid")

    @beartype
    def write_refreshed_access_token_to_redis(self) -> None:
        """Writes retrieved strava access token to redis."""
        logger.info("Refreshing strava access token")
        strava_secret_token = get_secret(environ["STRAVA_SECRET"])
        strava_access_token = self.get_strava_access_token(
            client_id=strava_secret_token["client_id"],
            client_secret=strava_secret_token["client_secret"],
            code=environ["AUTHORIZATION_TOKEN"],
            grant_type=strava_secret_token["grant_type"],
        )
        self.redis.write_redis(
            key=StravaKeys.STRAVA_ACCESS_TOKEN.value,
            value=strava_access_token,
            ttl=strava_access_token["expires_in"] - 60,
        )
        logger.info("Refreshed strava access token")

    @beartype
    def instantiate_strava_lib(self, strava_access_dict_from_redis: dict):
        """Instantiate strava client."""
        strava_access_token = (
            strava_access_dict_from_redis["access_token"]
            if strava_access_dict_from_redis
            else None
        )
        if not strava_access_token:
            return None
        self.strava_client = Client(access_token=strava_access_token)

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
            self.client.query(create_get_latest_activity_date_query(self.athlete_id))
            .to_dataframe()
            .iloc[0, 0]
        )
        activities = list(self.strava_client.get_activities(after=latest_activity_date))
        for activity in tqdm(activities, desc="Getting activities"):
            self.get_athlete_activity_streams(activity)
