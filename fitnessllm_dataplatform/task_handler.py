from os import environ

import fire
from beartype import beartype
from cloudpathlib import GSClient

from fitnessllm_dataplatform.entities.enums import DynamicEnum, FitnessLLMDataSource
from fitnessllm_dataplatform.infrastructure.RedisConnect import RedisConnect
from fitnessllm_dataplatform.stream.strava.services.api_interface import (
    StravaAPIInterface,
)
from fitnessllm_dataplatform.stream.strava.services.etl_interface import (
    StravaETLInterface,
)
from fitnessllm_dataplatform.utils.cloud_utils import get_secret
from fitnessllm_dataplatform.utils.logging_utils import logger


class Startup:
    def _startUp(self) -> None:
        logger.info("Starting up...")
        GSClient().set_as_default_client()
        self.InfrastructureNames = DynamicEnum.from_dict(
            get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]],
        )
        self.redis = RedisConnect()

    def __init__(self) -> None:
        self._startUp()

    @beartype
    def ingest(self, data_source: str) -> None:
        """Entry point for downloading JSONs from API.

        Args:
            data_source: Data source to download from.

        Raises:
            KeyError: If required options or environment variables are missing.
            ValueError: If data source is not supported.
        """
        if data_source not in [member.value for member in FitnessLLMDataSource]:
            raise ValueError(f"Unsupported data source: {data_source}")
        strava_api_interface = StravaAPIInterface(self.InfrastructureNames)
        try:
            strava_api_interface.get_all_activities()
        except Exception as e:
            raise RuntimeError(f"Failed to get data from Strava API: {e}") from e

    @beartype
    def etl(
        self, data_source: str, athlete_id: int, data_streams: list[str] | None = None
    ) -> None:
        """Entry point for loading JSONs into BigQuery."""

        if data_source == FitnessLLMDataSource.STRAVA.value:
            strava_etl_interface = StravaETLInterface(
                infrastructure_names=self.InfrastructureNames,
                athlete_id=str(athlete_id),
                data_streams=data_streams,
            )
            strava_etl_interface.load_json_into_bq()
        else:
            raise ValueError(f"Unsupported data source: {data_source}")


if __name__ == "__main__":
    fire.Fire(Startup)
