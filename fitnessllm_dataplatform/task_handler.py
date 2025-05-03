"""Main entry point for the data platform."""
from functools import partial
from os import environ

import fire
from beartype import beartype
from cloudpathlib import GSClient

from cloud_functions.token_refresh.utils.task_utils import decrypt_token
from fitnessllm_dataplatform.entities.enums import DynamicEnum, FitnessLLMDataSource
from fitnessllm_dataplatform.infrastructure.FirebaseConnect import FirebaseConnect
from fitnessllm_dataplatform.stream.strava.services.api_interface import (
    StravaAPIInterface,
)
from fitnessllm_dataplatform.stream.strava.services.bronze_etl_interface import (
    BronzeStravaETLInterface,
)
from fitnessllm_dataplatform.stream.strava.services.silver_etl_interface import (
    SilverStravaETLInterface,
)
from fitnessllm_dataplatform.utils.cloud_utils import get_secret
from fitnessllm_dataplatform.utils.logging_utils import logger


class Startup:
    """Main entry point for the data platform."""

    def _startUp(self, uid: str) -> None:
        """Resources agnostic of service."""
        logger.info("Starting up...")
        self.initialized = True
        GSClient().set_as_default_client()
        self.InfrastructureNames = DynamicEnum.from_dict(
            get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]],
        )
        self.firebase = FirebaseConnect(uid)
        self.decryptor = partial(
            decrypt_token, key=get_secret(environ["ENCRYPTION_SECRET"])["token"]
        )
        self.user_data = self.firebase.read_user().get().to_dict()

    def __init__(self) -> None:
        """Initializes the data platform."""
        self.initialized = False
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
        if not self.initialized:
            self._startUp(uid)

        if data_source not in [member.value for member in FitnessLLMDataSource]:
            raise ValueError(f"Unsupported data source: {data_source}")

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_user_data = self.firebase.read_user().collection("stream").document(data_source.lower()).get().to_dict()
            if strava_user_data is None:
                raise ValueError(f"User {uid} has no {data_source} data")

            strava_api_interface = StravaAPIInterface(
                infrastructure_names=self.InfrastructureNames,
                access_token=self.decryptor(
                    encrypted_token=strava_user_data["accessToken"]
                ),
                firebase=self.firebase,
            )
            try:
                strava_api_interface.get_all_activities()
            except Exception as e:
                raise RuntimeError(f"Failed to get data from Strava API: {e}") from e

    @beartype
    def bronze_etl(
        self, uid: str, data_source: str, data_streams: list[str] | None = None
    ) -> None:
        """Entry point for loading JSONs into bronze layer.

        Args:
            uid: Uid for user found in firebase.
            data_source: Data source to download from (e.g. Strava).
            data_streams: List of data streams to load.

        Raises:
            KeyError: If required data_source is not supported.
        """
        if not self.initialized:
            self._startUp(uid)

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_user_data = self.firebase.read_user().collection("stream").document(data_source.lower()).get().to_dict()
            strava_etl_interface = BronzeStravaETLInterface(
                infrastructure_names=self.InfrastructureNames,
                athlete_id=str(strava_user_data["athleteId"]),
                data_streams=data_streams,
            )
            strava_etl_interface.load_json_into_bq()
        else:
            raise ValueError(f"Unsupported data source: {data_source}")

    @beartype
    def silver_etl(self, uid: str, data_source: str) -> None:
        """Entry point for loading data from bronze to silver.

        Args:
            uid: Uid for user found in firebase.
            data_source: Data source to download from (e.g. Strava)

        Raises:
            KeyError: If required data_source is not supported.
        """
        if not self.initialized:
            self._startUp(uid)

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_user_data = self.firebase.read_user().collection("stream").document(data_source.lower()).get().to_dict()
            strava_etl_interface = SilverStravaETLInterface(
                athlete_id=str(strava_user_data["athleteId"]),
            )
            strava_etl_interface.task_handler()
        else:
            raise ValueError(f"Unsupported data source: {data_source}")

    @beartype
    def full_etl(
        self, uid: str, data_source: str, data_streams: list[str] | None = None
    ) -> None:
        """Entry point for full ETL process.

        Args:
            uid: Uid for user found in firebase.
            data_source: Data source to download from (e.g. Strava)
            data_streams: List of data streams to load for bronze ETL. If None, all streams will be loaded.

        Raises:
            KeyError: If required data_source is not supported.
        """
        # Ingest data
        self.ingest(uid=uid, data_source=data_source)

        # Bronze ETL
        self.bronze_etl(uid=uid, data_source=data_source, data_streams=data_streams)

        # Silver ETL
        self.silver_etl(uid=uid, data_source=data_source)

        logger.info("Full ETL process completed successfully.")


if __name__ == "__main__":
    fire.Fire(Startup)
