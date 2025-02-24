"""This module contains queries for the Strava stream."""

from beartype import beartype

from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
)


@beartype
def create_activities_query(
    athlete_id: str,
    env: str,
    data_source: FitnessLLMDataSource,
    data_stream: FitnessLLMDataStream,
) -> str:
    """Create a query to get all activities for a specific athlete."""
    schema_name = f"{env}_bronze_{data_source.value.lower()}"
    return f"""
        SELECT DISTINCT activity_id
        FROM {schema_name}.metrics
        WHERE athlete_id = '{athlete_id}' and data_source = '{data_source.value}' and data_stream = '{data_stream.value}' and status = 'SUCCESS'
    """


@beartype
def create_get_latest_activity_date_query(
    env: str, athlete_id: str, data_source: FitnessLLMDataSource
) -> str:
    """Create a query to get the latest activity date for a specific athlete."""
    schema_name = f"{env}_bronze_{data_source.value.lower()}"
    return f"""
        SELECT MAX(start_date)
        FROM {schema_name}.activity
        WHERE athlete_id = '{athlete_id}'
    """
