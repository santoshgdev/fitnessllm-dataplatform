"""Main entry point for the data platform."""
import traceback
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
from fitnessllm_dataplatform.utils.logging_utils import structured_logger


class Startup:
    """Main entry point for the data platform."""

    def _startUp(self, uid: str) -> None:
        """Resources agnostic of service."""
        structured_logger.info(message="Starting up data platform", uid=uid)
        self.initialized = True
        GSClient().set_as_default_client()
        self.InfrastructureNames = DynamicEnum.from_dict(
            get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]],
        )
        self.firebase = FirebaseConnect(uid)
        self.decryptor = partial(
            decrypt_token,
            key=get_secret(environ["ENCRYPTION_SECRET"])["token"],
        )
        self.user_data = self.firebase.read_user().get().to_dict()

    def __init__(self) -> None:
        """Initializes the data platform."""
        self.initialized = False

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
            structured_logger.error(
                message="Unsupported data source", data_source=data_source, uid=uid
            )
            raise ValueError(f"Unsupported data source: {data_source}")

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_user_data = (
                self.firebase.read_user()
                .collection("stream")
                .document(data_source.lower())
                .get()
                .to_dict()
            )
            if strava_user_data is None:
                structured_logger.error(
                    message="User has no data",
                    uid=uid,
                    data_source=data_source,
                    traceback=traceback.format_exc(),
                )
                raise ValueError(f"User {uid} has no {data_source} data")

            strava_api_interface = StravaAPIInterface(
                uid=uid,
                infrastructure_names=self.InfrastructureNames,
                access_token=self.decryptor(
                    encrypted_token=strava_user_data["accessToken"]
                ),
                firebase=self.firebase,
            )
            try:
                strava_api_interface.get_all_activities()
            except Exception as e:
                structured_logger.error(
                    message="Failed to get data from API",
                    uid=uid,
                    data_source=data_source,
                    exception=e,
                    traceback=traceback.format_exc(),
                )
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
            strava_user_data = (
                self.firebase.read_user()
                .collection("stream")
                .document(data_source.lower())
                .get()
                .to_dict()
            )

            if strava_user_data is None:
                structured_logger.error(
                    message="User has no data", uid=uid, data_source=data_source
                )
                raise ValueError(f"User {uid} has no {data_source} data")
            if (
                "athlete" not in strava_user_data
                or "id" not in strava_user_data["athlete"]
            ):
                structured_logger.error(
                    message="User has incomplete data: missing athleteId",
                    uid=uid,
                    data_source=data_source,
                )
                raise ValueError(
                    f"User {uid} has incomplete {data_source} data: missing athlete ID"
                )

            strava_etl_interface = BronzeStravaETLInterface(
                uid=uid,
                infrastructure_names=self.InfrastructureNames,
                athlete_id=str(strava_user_data["athlete"]["id"]),
                data_streams=data_streams,
            )
            strava_etl_interface.load_json_into_bq()
        else:
            structured_logger.error(
                "Unsupported data source", uid=uid, data_source=data_source
            )
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
            strava_user_data = (
                self.firebase.read_user()
                .collection("stream")
                .document(data_source.lower())
                .get()
                .to_dict()
            )

            if strava_user_data is None:
                structured_logger.error(
                    message="User has no data", uid=uid, data_source=data_source
                )
                raise ValueError(f"User {uid} has no {data_source} data")
            if (
                "athlete" not in strava_user_data
                or "id" not in strava_user_data["athlete"]
            ):
                structured_logger.error(
                    message="User has incomplete data: missing athleteId",
                    uid=uid,
                    data_source=data_source,
                )
                raise ValueError(
                    f"User {uid} has incomplete {data_source} data: missing athlete ID"
                )

            strava_etl_interface = SilverStravaETLInterface(
                uid=uid,
                athlete_id=str(strava_user_data["athlete"]["id"]),
            )
            strava_etl_interface.task_handler()
        else:
            structured_logger.error(
                "Unsupported data source", uid=uid, data_source=data_source
            )
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

        structured_logger.info(
            "Full ETL process completed successfully", uid=uid, data_source=data_source
        )


if __name__ == "__main__":
    fire.Fire(Startup)
