from beartype import beartype

from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
)


@beartype
def create_activities_query(
    athlete_id: str,
    data_source: FitnessLLMDataSource,
    data_stream: FitnessLLMDataStream,
) -> str:
    return f"""
        SELECT DISTINCT activity_id
        FROM dev_metrics.metrics
        WHERE athlete_id = '{athlete_id}' and data_source = '{data_source.value}' and data_stream = '{data_stream.value}' and status = 'SUCCESS'
    """


@beartype
def create_get_latest_activity_date_query(
        athlete_id: str
) -> str:
    return f"""
        SELECT MAX(start_date)
        FROM dev_strava.activity
        WHERE athlete_id = '{athlete_id}'
    """