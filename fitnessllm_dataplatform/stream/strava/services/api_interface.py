import json
from enum import Enum
from functools import partial
from os import environ

import requests
from stravalib import Client
from stravalib.model import Stream
from tqdm import tqdm

from fitnessllm_dataplatform.infrastructure.RedisConnect import RedisConnect
from fitnessllm_dataplatform.services.api_interface import APIInterface
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaKeys, StravaURLs, StravaStreams
from fitnessllm_dataplatform.utils.cloud_utils import get_secret, write_json_to_storage
from fitnessllm_dataplatform.utils.logging_utils import logger
from fitnessllm_dataplatform.utils.reques_utils import handle_status_code
from fitnessllm_dataplatform.utils.task_utils import get_enum_values_from_list


class StravaAPIInterface(APIInterface):
    def __init__(self, redis = None):
        super().__init__()
        self.client = None
        self.redis = redis or RedisConnect()
        self.refresh_access_token_at_expiration()
        strava_access_token_dict = self.redis.read_redis(StravaKeys.STRAVA_ACCESS_TOKEN.value)
        self.instantiate_strava_lib(strava_access_token_dict)


    @staticmethod
    def get_strava_access_token(client_id: str,
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

    def refresh_access_token_at_expiration(self):
        """Refreshes strava access token if it happens to be expired."""
        redis_ttl = self.redis.get_ttl(StravaKeys.STRAVA_ACCESS_TOKEN.value)
        if redis_ttl is None or redis_ttl < 0:
            self.write_refreshed_access_token_to_redis()
        else:
            logger.info("Strava token still valid")

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
    
    
    def instantiate_strava_lib(self, strava_access_dict_from_redis: dict):
        """Instantiate strava client."""
        strava_access_token = (
            strava_access_dict_from_redis["access_token"]
            if strava_access_dict_from_redis
            else None
        )
        if not strava_access_token:
            return None
        self.client = Client(access_token=strava_access_token)
    
    
    def get_all_data(self, InfrastructureNames: Enum) -> str | None:
        """Get all activities."""
        athlete = self.client.get_athlete()
        athlete_id = athlete.id
        partial_get_strava_storage = partial(
            get_strava_storage_path,
            bucket=InfrastructureNames.bronze_bucket,
            athlete_id=athlete_id
        )

        path = partial_get_strava_storage(strava_model=StravaStreams.ATHLETE_SUMMARY)
        write_json_to_storage(path, athlete.model_dump_json())

        activities = list(self.client.get_activities())
        for activity in tqdm(activities, desc="Getting activities"):
            activity_dump = activity.model_dump()
            athlete_id, activity_id = activity_dump["athlete"]["id"], activity_dump["id"]
            path = partial_get_strava_storage(strava_model=StravaStreams.ACTIVITY, activity_id=activity_id)
            write_json_to_storage(path, json.loads(activity.model_dump_json()))

            non_activity_streams = StravaStreams.filter_streams(exclude=['ACTIVITY','ATHLETE_SUMMARY'])
            streams = self.client.get_activity_streams(
                activity_id=activity_id, types=get_enum_values_from_list(non_activity_streams)
            )
            for stream in non_activity_streams:
                stream_data = streams.get(stream.value, Stream())
                path = partial_get_strava_storage(strava_model=stream, activity_id=activity_id)
                write_json_to_storage(path, stream_data.model_dump_json())
        return athlete_id

