from os import environ

import fire

from fitnessllm_dataplatform.entities.enums import DynamicEnum
from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource
from fitnessllm_dataplatform.stream.strava.etl_utils import load_json_into_bq
from fitnessllm_dataplatform.utils.task_utils import load_into_env_vars
from fitnessllm_dataplatform.utils.cloud_utils import get_secret
from cloudpathlib import GSClient


def handler(options: dict) -> None:
    """Entry point for the application."""
    load_into_env_vars(options)
    GSClient().set_as_default_client()

    InfrastructureNames = DynamicEnum.from_dict(
        get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]]
    )

    if options['data_source'] == FitnessLLMDataSource.STRAVA.value:
        athlete_id = options['athlete_id']
        load_json_into_bq(InfrastructureNames=InfrastructureNames, athlete_id=athlete_id, data_streams=options.get('data_streams'))


if __name__ == '__main__':
    fire.Fire(handler)