"""Utility functions for ETL operations on Strava data."""

from beartype import beartype
from beartype.typing import Callable
from pandas import DataFrame

from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams


@beartype
def latlng_etl(df: DataFrame) -> DataFrame:
    """ETL operations for latlng data stream."""
    df["latitude"] = df["data"].apply(lambda x: x[0])
    df["longitude"] = df["data"].apply(lambda x: x[1])
    df.drop(columns=["data"], inplace=True)
    return df


@beartype
def activity_etl(df: DataFrame) -> DataFrame:
    """ETL operations for activity data stream."""
    df["start_latitude"] = df["start_latlng"].apply(lambda x: x[0] if x else None)
    df["start_longitude"] = df["start_latlng"].apply(lambda x: x[1] if x else None)
    df["end_latitude"] = df["end_latlng"].apply(lambda x: x[0] if x else None)
    df["end_longitude"] = df["end_latlng"].apply(lambda x: x[1] if x else None)
    df.drop(columns=["start_latlng", "end_latlng"], inplace=True)
    return df


def get_etl_func(stream: StravaStreams) -> list[Callable]:
    """Returns the ETL function for a given stream."""
    return ETL_MAP.get(stream, [])


@beartype
def execute_etl_func(stream: StravaStreams, df: DataFrame) -> DataFrame:
    """Executes the ETL functions for a given stream."""
    etl_funcs = get_etl_func(stream)
    for etl_func in etl_funcs:
        df = etl_func(df)
    return df


ETL_MAP = {
    StravaStreams.LATLNG: [latlng_etl],
    StravaStreams.ACTIVITY: [activity_etl],
}
