"""ETL Utilities for Strava Data Source."""
import itertools
import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from functools import partial
from os import environ

import pandas as pd
from cloudpathlib import GSPath
from google.cloud import bigquery
from joblib import Parallel, delayed
from pandas import DataFrame
from tqdm import tqdm
from tqdm_joblib import tqdm_joblib
import multiprocessing as mp

from fitnessllm_dataplatform.entities.dataclasses import Metrics
from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream, Status,
)
from fitnessllm_dataplatform.entities.queries import get_activities
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.utils.logging_utils import logger


def load_json_into_bq(InfrastructureNames: Enum, athlete_id: str, data_streams: list[str]):
    partial_strava_storage = partial(
        get_strava_storage_path,
        bucket=InfrastructureNames.bronze_bucket,
        athlete_id=athlete_id,
    )

    partial_load_json_into_dataframe = partial(
        load_json_into_dataframe,
        athlete_id=athlete_id,
        data_source=FitnessLLMDataSource.STRAVA,
    )
    client = bigquery.Client()

    streams = [
        element.name for element in partial_strava_storage(strava_model=None).iterdir() if element.name in data_streams
    ]
    for stream in streams:
        stream_enum = StravaStreams[stream.upper()]
        activity_ids = client.query(get_activities(athlete_id=athlete_id,
                                                   data_source=FitnessLLMDataSource.STRAVA,
                                                   data_stream=stream_enum)).to_dataframe()['activity_id'].values

        module_strava_json_list = list(itertools.islice(partial_strava_storage(strava_model=stream_enum).iterdir(), int(environ['SAMPLE']))) if environ.get('SAMPLE') else list(partial_strava_storage(strava_model=stream_enum).iterdir())
        filtered_module_strava_json_list = [file for file in module_strava_json_list if file.stem.split("=")[1] not in activity_ids]

        with tqdm_joblib(tqdm(desc=f"Processing {stream}", total=len(filtered_module_strava_json_list))):
            result = Parallel(n_jobs=1, backend="threading")(
                delayed(partial_load_json_into_dataframe)(file=json_file, data_stream=stream)
                for json_file in filtered_module_strava_json_list
            )

        dataframes = pd.concat([result["dataframe"] for result in result])
        metrics = [result["metrics"] for result in result]
        timestamp = datetime.now()

        try:
            client.load_table_from_dataframe(dataframe=dataframes,
                                             destination=f"dev_strava.{stream}",
                                             job_config=bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND))
            insert_metrics(metrics_list=metrics,
                           destination=f"dev_strava.metrics",
                           timestamp=timestamp,
                           status=Status.SUCCESS)
        except Exception as e:
            logger.error(f"Error while inserting for {stream_enum.value} for {athlete_id}: {e}")
            insert_metrics(metrics_list=metrics,
                           destination=f"dev_strava.metrics",
                           timestamp=timestamp,
                           status=Status.FAILURE)



def insert_metrics(metrics_list: list[Metrics],
                   destination: str,
                   timestamp: datetime,
                   status: Status):
    try:
        client = bigquery.Client()
        metrics_list = [asdict(metrics.update(bq_insert_timestamp=timestamp, status=status.value)) for metrics in metrics_list]
        dataframe = pd.DataFrame(metrics_list)
        client.load_table_from_dataframe(dataframe=dataframe,
                                         destination=destination,
                                         job_config=bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND))
    except Exception as e:
        logger.error("Unable to write metrics to BigQuery.")
        raise e




def process_json(input_dict: dict) -> dict:
    if isinstance(input_dict["data"], dict):
        data = input_dict["data"]
        if data.get("map"):
            del data["map"]
        if data.get("athlete"):
            del data["athlete"]

        data["athlete_id"] = input_dict["athlete_id"]
        data["activity_id"] = input_dict["activity_id"]
        for k, v in data.items():
            if type(v) in [list]:
                data[k] = str(v)
        return data
    if isinstance(input_dict["data"], list):
        for element in input_dict["data"]:
            element["athlete_id"] = input_dict["athlete_id"]
            element["activity_id"] = input_dict["activity_id"]
            for k, v in element.items():
                if type(v) in [list]:
                    element[k] = str(v)
        return input_dict["data"]


def load_json_into_dataframe(
    athlete_id: str, file: GSPath, data_source, data_stream: FitnessLLMDataStream
) -> dict[str, DataFrame| Metrics]:
    loaded_json = {
        "athlete_id": athlete_id,
        "activity_id": file.stem.split("=")[1],
        "data": json.loads(file.read_text()),
    }
    processed_list_of_jsons = process_json(loaded_json)
    partial_metrics = partial(Metrics,
                              athlete_id=athlete_id,
                              activity_id=file.stem.split("=")[1],
                              data_source=data_source.value,
                              data_stream=data_stream)

    if isinstance(processed_list_of_jsons, list):
        dataframe = DataFrame(processed_list_of_jsons)
        return {"dataframe": dataframe, "metrics": partial_metrics(record_count=dataframe.shape[0])}
    output = list(itertools.chain(*processed_list_of_jsons))
    dataframe = DataFrame(output)
    return {"dataframe": dataframe, "metrics": partial_metrics(record_count=dataframe.shape[0])}