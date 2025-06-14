"""Main entry point for the data platform."""

import traceback
from functools import partial
from os import environ
from typing import Optional

import fire
from beartype import beartype
from cloudpathlib import GSClient
from fitnessllm_shared.logger_utils import structured_logger
from fitnessllm_shared.task_utils import decrypt_token

from fitnessllm_dataplatform.entities.enums import DynamicEnum, FitnessLLMDataSource
from fitnessllm_dataplatform.infrastructure.FirebaseConnect import FirebaseConnect
from fitnessllm_dataplatform.stream.strava.qc_utils import check_firebase_strava_data
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


class ProcessUser:
    """Main entry point for the data platform."""

    def __init__(self, uid: str, data_source: str) -> None:
        """Initializes the data platform.

        Args:
            uid: User ID for the current operation
            data_source: Data source to process
        """
        self.uid = uid
        self.data_source = data_source

        structured_logger.info(
            message="Starting up data platform", **self._get_common_fields()
        )
        GSClient().set_as_default_client()
        self.InfrastructureNames = DynamicEnum.from_dict(
            get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]],
        )
        self.firebase = FirebaseConnect(uid=self.uid)
        self.decryptor = partial(
            decrypt_token,
            key=get_secret(environ["ENCRYPTION_SECRET"])["token"],
        )

    def _get_common_fields(self) -> dict:
        """Get a logger with common fields.

        Returns:
            Dict of common logging fields
        """
        fields = {
            "uid": self.uid,
            "data_source": self.data_source,
            "service_name": "task_handler",
        }
        return fields

    @staticmethod
    def _get_exception_fields(e: Exception) -> dict:
        """Get a logger with exception fields.

        Returns:
            Dict of exception logging fields
        """
        fields = {
            "exception": str(e),
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        return fields

    def _get_firebase_data_source_document(
        self, data_source: FitnessLLMDataSource
    ) -> dict:
        """Get the firebase document for a given data source.

        Args:
            data_source: Data source to get document for.

        Returns:
            Dict of firebase document
        """
        document = (
            self.firebase.read_user()
            .collection("stream")
            .document(data_source.value.lower())
            .get()
            .to_dict()
        )
        if document is None:
            structured_logger.error(
                message="User has no data", **self._get_common_fields()
            )
            raise ValueError(f"User {self.uid} has no {data_source.value} data")
        return document

    @beartype
    def ingest(self) -> None:
        """Entry point for downloading JSONs from API.

        Args:
            uid: Uid for user found in firebase.
            data_source: Data source to download from.

        Raises:
            KeyError: If required options or environment variables are missing.
            ValueError: If data source is not supported.
        """
        if self.data_source not in [member.value for member in FitnessLLMDataSource]:
            structured_logger.error(
                message="Unsupported data source", **self._get_common_fields()
            )
            raise ValueError(f"Unsupported data source: {self.data_source}")

        if self.data_source == FitnessLLMDataSource.STRAVA.value:
            self._strava_ingest_etl()

    @beartype
    def bronze_etl(self) -> None:
        """Entry point for loading JSONs into bronze layer.

        Raises:
            KeyError: If required data_source is not supported.
        """
        if self.data_source == FitnessLLMDataSource.STRAVA.value:
            self._strava_bronze_etl()
        else:
            structured_logger.error(
                "Unsupported data source", **self._get_common_fields()
            )
            raise ValueError(f"Unsupported data source: {self.data_source}")

    @beartype
    def silver_etl(self) -> None:
        """Entry point for loading data from bronze to silver.

        Raises:
            KeyError: If required data_source is not supported.
        """
        if self.data_source == FitnessLLMDataSource.STRAVA.value:
            self._strava_silver_etl()
        else:
            structured_logger.error(
                "Unsupported data source", **self._get_common_fields()
            )
            raise ValueError(f"Unsupported data source: {self.data_source}")

    @beartype
    def full_etl(self, data_streams: Optional[list[str]] = None) -> None:
        """Entry point for full ETL process.

        Args:
            data_streams: List of data streams to load for bronze ETL. If None, all streams will be loaded.

        Raises:
            KeyError: If required data_source is not supported.
        """
        # Ingest data
        self.ingest()

        # Bronze ETL
        self.bronze_etl(data_streams=data_streams)

        # Silver ETL
        self.silver_etl()

        structured_logger.info(
            "Full ETL process completed successfully", **self._get_common_fields()
        )

    @beartype
    def _strava_ingest_etl(self) -> None:
        """Ingest ETL for Strava."""
        strava_user_data = self._get_firebase_data_source_document(
            data_source=FitnessLLMDataSource.STRAVA
        )
        if strava_user_data is None:
            structured_logger.error(
                message="User has no data", **self._get_common_fields()
            )
            raise ValueError(f"User {self.uid} has no {self.data_source} data")

        strava_api_interface = StravaAPIInterface(
            uid=self.uid,
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
                **self._get_exception_fields(e),
                **self._get_common_fields(),
            )
            raise RuntimeError(f"Failed to get data from Strava API: {e}") from e

    @beartype
    def _strava_bronze_etl(self, data_streams: Optional[list[str]] = None) -> None:
        """Bronze ETL for Strava."""
        strava_user_data = self._get_firebase_data_source_document(
            data_source=FitnessLLMDataSource.STRAVA
        )

        check_firebase_strava_data(strava_user_data, **self._get_common_fields())

        strava_etl_interface = BronzeStravaETLInterface(
            uid=self.uid,
            infrastructure_names=self.InfrastructureNames,
            athlete_id=str(strava_user_data["athlete"]["id"]),
            data_streams=data_streams,
        )
        strava_etl_interface.load_json_into_bq()

    @beartype
    def _strava_silver_etl(self) -> None:
        """Silver ETL for Strava."""
        strava_user_data = self._get_firebase_data_source_document(
            data_source=FitnessLLMDataSource.STRAVA
        )

        check_firebase_strava_data(strava_user_data, **self._get_common_fields())

        strava_etl_interface = SilverStravaETLInterface(
            uid=self.uid,
            athlete_id=str(strava_user_data["athlete"]["id"]),
        )
        strava_etl_interface.task_handler()


if __name__ == "__main__":
    # Example usage:
    # python task_handler.py --uid=user123 --data_source=strava ingest
    # python task_handler.py --uid=user123 --data_source=strava bronze_etl
    # python task_handler.py --uid=user123 --data_source=strava silver_etl
    # python task_handler.py --uid=user123 --data_source=strava full_etl
    fire.Fire(ProcessUser)
