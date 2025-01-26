import json
from enum import Enum
from functools import partial
import itertools

from google.cloud.bigquery import SchemaField
from tqdm import tqdm

import pandas as pd
from cloudpathlib import GSPath

from stream.strava.cloud_utils import get_strava_storage_path
from stream.strava.entities.enums import StravaStreams
from pandas_gbq import to_gbq
from google.cloud import bigquery


def load_json_into_bq(InfrastructureNames: Enum, athlete_id: str, batch_size: int = 10, pandas_gbq=None):
    partial_strava_storage = partial(get_strava_storage_path,
                                     bucket=InfrastructureNames.bronze_bucket,
                                     athlete_id=athlete_id)
    client = bigquery.Client()

    streams = [element.name for element in partial_strava_storage(strava_model=None).iterdir()]
    streams = ['activity']
    for stream in streams:
        stream_enum = StravaStreams[stream.upper()]
        module_strava_json_list = list(partial_strava_storage(strava_model=stream_enum).iterdir())
        for i in tqdm(range(0, len(module_strava_json_list), batch_size), desc = f"{stream}"):
            batched_dataframe = load_batch_jsons_into_dataframe(athlete_id=athlete_id,
                                                                batch=module_strava_json_list[i:i + batch_size])
            table = client.get_table(f"dev_strava.{stream}")
            table_schema = table.schema[:]

            new = set(batched_dataframe.columns) - set([e.name for e in table.schema])
            for new_col in new:
                table_schema.append(SchemaField(new_col, "STRING", mode="nullable"))
            client.update_table(table, ["schema"])

            to_gbq(batched_dataframe, f"dev_strava.{stream}",  if_exists='append')


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

def load_batch_jsons_into_dataframe(athlete_id: str, batch: list[GSPath]) -> list[pd.DataFrame]:
    list_of_jsons = [{'athlete_id': athlete_id, 'activity_id': file.stem.split("=")[1], 'data': json.loads(file.read_text())} for file in batch]
    processed_list_of_jsons = [process_json(file) for file in list_of_jsons]
    if isinstance(processed_list_of_jsons[0], list):
        output = list(itertools.chain(*processed_list_of_jsons))
        return pd.DataFrame(output)
    else:
        return pd.DataFrame(processed_list_of_jsons)
