from os import environ
from typing import Any

import fire
from cloudpathlib import GSClient

from fitnessllm_dataplatform.entities.enums import DynamicEnum
from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource
from fitnessllm_dataplatform.stream.strava.etl_utils import load_json_into_bq
from fitnessllm_dataplatform.stream.strava.services.api_interface import StravaAPIInterface
from fitnessllm_dataplatform.utils.cloud_utils import get_secret
from fitnessllm_dataplatform.utils.logging_utils import logger
from fitnessllm_dataplatform.utils.task_utils import load_into_env_vars


class Startup:
    def __init__(self, options: dict[str, Any]) -> None:
        logger.info("Starting up...")
        load_into_env_vars(options)
        GSClient().set_as_default_client()
        self.InfrastructureNames = DynamicEnum.from_dict(
            get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]]
        )

    def ingest(self, options: dict[str, Any]) -> None:
        """Entry point for downloading JSONs from API."""

        if options['data_source'] == FitnessLLMDataSource.STRAVA.value:
            strava_api_interface = StravaAPIInterface()
            strava_api_interface.get_all_data(self.InfrastructureNames)


    def etl(self, options: dict) -> None:
        """Entry point for loading JSONs into BigQuery."""

        if options['data_source'] == FitnessLLMDataSource.STRAVA.value:
            athlete_id = options['athlete_id']
            load_json_into_bq(InfrastructureNames=self.InfrastructureNames, athlete_id=athlete_id, data_streams=options.get('data_streams'))


if __name__ == '__main__':
    fire.Fire(Startup)