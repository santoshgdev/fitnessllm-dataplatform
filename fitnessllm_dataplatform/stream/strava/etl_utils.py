import json
from dataclasses import dataclass
from enum import Enum
from functools import partial
import itertools

from pandas import DataFrame
from redis.typing import FieldT
from tqdm import tqdm
from cloudpathlib import GSPath

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataStreams
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from google.cloud import bigquery

def load_json_into_bq(InfrastructureNames: Enum, athlete_id: str):
    partial_strava_storage = partial(get_strava_storage_path,
                                     bucket=InfrastructureNames.bronze_bucket,
                                     athlete_id=athlete_id)
    client = bigquery.Client()

    streams = [element.name for element in partial_strava_storage(strava_model=None).iterdir()]
    for stream in streams:
        stream_enum = StravaStreams[stream.upper()]
        module_strava_json_list = list(partial_strava_storage(strava_model=stream_enum).iterdir())
        for json_file in tqdm(module_strava_json_list, desc = f"{stream}"):
            batched_dataframe = load_batch_jsons_into_dataframe(athlete_id=athlete_id,
                                                                file=json_file,
                                                                data_source = FitnessLLMDataStreams.STRAVA,
                                                                data)
            client.load_table_from_dataframe(dataframe=batched_dataframe,
                                             destination=f"dev_strava.{stream}",
                                             job_config=bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND))

@dataclass
class Metrics:
    athlete_id: str
    activity_id: str
    data_source: str
    stream: str
    record_count: int
    status: str
    bq_insert_timestamp: str


def insert_metrics(**kwargs):

    athlete_id = kwargs.get('athlete_id')
    activity_id = kwargs.get('activity_id')
    data_source = kwargs.get('data_source')
    stream = kwargs.get('stream')
    record_count = kwargs.get('record_count')
    status = kwargs.get('status')
    bq_insert_timestamp = kwargs.get('bq_insert_timestamp')




def process_json(input_dict: dict) -> dict:
    if isinstance(input_dict['data'], dict):
        data = input_dict['data']
        if data.get('map'):
            del data['map']
        if data.get('athlete'):
            del data['athlete']

        data['athlete_id'] = input_dict['athlete_id']
        data['activity_id'] = input_dict['activity_id']
        for k, v in data.items():
            if type(v) in [list]:
                data[k] = str(v)
        return data
    if isinstance(input_dict['data'], list):
        for element in input_dict['data']:
            element['athlete_id'] = input_dict['athlete_id'];
            element['activity_id'] = input_dict['activity_id']
            for k, v in element.items():
                if type(v) in [list]:
                    element[k] = str(v)
        return input_dict['data']

def load_batch_jsons_into_dataframe(athlete_id: str, file: GSPath, data_source = FitnessLLMDataStreams.STRAVA) -> DataFrame:
    loaded_json = {'athlete_id': athlete_id, 'activity_id': file.stem.split("=")[1], 'data': json.loads(file.read_text())}
    processed_list_of_jsons = process_json(loaded_json)
    if not isinstance(processed_list_of_jsons[0], list):
        return DataFrame(processed_list_of_jsons)
    output = list(itertools.chain(*processed_list_of_jsons))
    return DataFrame(output), Metrics(athlete_id=athlete_id, activity_id=file.stem.split("=")[1])
