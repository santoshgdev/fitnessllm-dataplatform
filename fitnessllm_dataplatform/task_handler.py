"""Main entry point for the data platform."""
import json
from functools import partial
from os import environ

import fire
from beartype import beartype
from cloudpathlib import GSClient

from fitnessllm_dataplatform.entities.enums import DynamicEnum, FitnessLLMDataSource
from fitnessllm_dataplatform.infrastructure.FirebaseConnect import FirebaseConnect
from fitnessllm_dataplatform.stream.strava.services.api_interface import (
    StravaAPIInterface,
)
from fitnessllm_dataplatform.stream.strava.services.bronze_etl_interface import (
    BronzeStravaETLInterface,
)
from fitnessllm_dataplatform.stream.strava.services.silver_etl_interface import SilverStravaETLInterface
from fitnessllm_dataplatform.utils.cloud_utils import get_secret
from fitnessllm_dataplatform.utils.logging_utils import logger
from fitnessllm_dataplatform.utils.task_utils import decrypt_token


class Startup:
    """Main entry point for the data platform."""

    def _startUp(self, uid: str) -> None:
        """Resources agnostic of service."""
        logger.info("Starting up...")
        GSClient().set_as_default_client()
        self.InfrastructureNames = DynamicEnum.from_dict(
            get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]],
        )
        self.firebase = FirebaseConnect(uid)
        self.decryptor = partial(decrypt_token, key=get_secret(environ["ENCRYPTION_SECRET"])['token'])

    def __init__(self) -> None:
        """Initializes the data platform."""
        pass

    @beartype
    def ingest(self, uid: str, data_source: str) -> None:
        """Entry point for downloading JSONs from API.

        Args:
            uid: Uid for user found in firebase.
            data_source: Data source to download from.

        Raises:
            KeyError: If required options or environment variables are missing.
            ValueError: If data source is not supported.
        """
        self._startUp(uid)
        user_data = self.firebase.read_user().get().to_dict()

        if data_source not in [member.value for member in FitnessLLMDataSource]:
            raise ValueError(f"Unsupported data source: {data_source}")

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_user_data = user_data.get(f"stream={data_source.lower()}")
            if strava_user_data is None:
                raise ValueError(f"User {uid} has no {data_source} data")

            strava_api_interface = StravaAPIInterface(infrastructure_names=self.InfrastructureNames,
                                                      access_token=self.decryptor(encrypted_token=strava_user_data['accessToken']),
                                                      firebase=self.firebase)
            try:
                strava_api_interface.get_all_activities()
            except Exception as e:
                raise RuntimeError(f"Failed to get data from Strava API: {e}") from e

    @beartype
    def bronze_etl(
        self, uid: str, data_source: str, data_streams: list[str] | None = None
    ) -> None:
        """Entry point for loading JSONs into bronze layer."""
        self._startUp(uid)
        user_data = self.firebase.read_user().get().to_dict()

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_user_data = user_data.get(f"stream={data_source.lower()}")
            strava_etl_interface = BronzeStravaETLInterface(
                infrastructure_names=self.InfrastructureNames,
                athlete_id=str(strava_user_data['athleteId']),
                data_streams=data_streams,
            )
            strava_etl_interface.load_json_into_bq()
        else:
            raise ValueError(f"Unsupported data source: {data_source}")

    @beartype
    def silver_etl(self, uid: str, data_source: str) -> None:
        """Entry point for loading data from bronze to silver."""
        self._startUp(uid)
        user_data = self.firebase.read_user().get().to_dict()

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_user_data = user_data.get(f"stream={data_source.lower()}")
            strava_etl_interface = SilverStravaETLInterface(
                athlete_id=str(strava_user_data['athleteId']),
            )
            strava_etl_interface.task_handler()


if __name__ == "__main__":
    fire.Fire(Startup)
