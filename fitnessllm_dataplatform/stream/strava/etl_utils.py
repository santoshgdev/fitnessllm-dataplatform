from beartype import beartype
from pandas import DataFrame

from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams


@beartype
def latlng_etl(df: DataFrame) -> DataFrame:
    df['latitude'] = df['data'].apply(lambda x: x[0])
    df['longitude'] = df['data'].apply(lambda x: x[1])
    return df.drop(columns=['data'])

@beartype
def activity_etl(df: DataFrame) -> DataFrame:
    df['max_watts'] = df['max_watts'].astype(float)
    df['average_watts'] = df['average_watts'].astype(float)
    return df


def get_etl_func(stream: StravaStreams) -> callable:
    return ETL_MAP.get(stream, [])

@beartype
def execute_etl_func(stream: StravaStreams, df: DataFrame) -> DataFrame:
    etl_funcs = get_etl_func(stream)
    for etl_func in etl_funcs:
        df = etl_func(df)
    return df


ETL_MAP = {
    StravaStreams.LATLNG: [latlng_etl],
    StravaStreams.ACTIVITY: [activity_etl],
}