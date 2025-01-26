from os import environ

import fire

from entities.enums import DynamicEnum
from enums import FitnessLLMDataStreams
from stream.strava.etl_utils import load_json_into_bq
from utils.task_utils import load_into_env_vars
from utils.cloud_utils import get_secret


def handler(options: dict) -> None:
    """Entry point for the application."""
    load_into_env_vars(options)

    InfrastructureNames = DynamicEnum.from_dict(
        get_secret(environ["INFRASTRUCTURE_SECRET"])[environ["STAGE"]]
    )

    if options['data_stream'] == FitnessLLMDataStreams.STRAVA.value:
        athlete_id = options['athlete_id']
        load_json_into_bq(InfrastructureNames=InfrastructureNames, athlete_id=athlete_id)


if __name__ == '__main__':
    fire.Fire(handler)