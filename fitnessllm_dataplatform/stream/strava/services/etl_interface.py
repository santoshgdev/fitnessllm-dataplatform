import itertools
import json
from dataclasses import asdict
from datetime import datetime
from enum import EnumType
from functools import partial
from os import environ

from beartype import beartype
from cloudpathlib import GSPath
from google.cloud import bigquery
from joblib import Parallel, delayed
from joblib._multiprocessing_helpers import mp
from pandas import DataFrame
from tqdm import tqdm
from tqdm_joblib import tqdm_joblib

from fitnessllm_dataplatform.entities.dataclasses import Metrics
from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource, FitnessLLMDataStream, Status
from fitnessllm_dataplatform.entities.queries import create_activities_query
from fitnessllm_dataplatform.services.etl_interface import ETLInterface
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.utils.logging_utils import logger


class StravaETLInterface(ETLInterface):

    def __init__(self, infrastructure_names: EnumType, athlete_id: str, data_streams: list[str] | None = None):
        super().__init__()
        self.data_source = FitnessLLMDataSource.STRAVA
        self.athlete_id = athlete_id
        self.data_streams = data_streams
        self.InfrastructureNames = infrastructure_names
        self.partial_strava_storage = partial(
            get_strava_storage_path,
            bucket=self.InfrastructureNames.bronze_bucket,
            athlete_id=athlete_id,
        )
        self.client = bigquery.Client()

    @beartype
    def load_json_into_bq(self) -> None:
        try:
            streams = [
                StravaStreams[element.name.upper()]
                for element in self.partial_strava_storage(strava_model=None).iterdir()
            ]
        except KeyError as exc:
            logger.error(f"User defined data_streams for Strava not found: {self.data_streams}: {exc}")
            raise exc

        if self.data_streams:
            streams = [stream for stream in streams if stream.value in self.data_streams]

        for stream in streams:
            logger.info(f"Loading {stream} for {self.athlete_id}")
            dataframes, metrics = self.convert_stream_json_to_dataframe(
                stream=stream
            )
            self.upsert_to_bigquery(
                stream=stream,
                dataframes=dataframes,
                metrics=metrics,
            )

    @beartype
    def convert_stream_json_to_dataframe(
            self,
            stream: StravaStreams
    ):
        sample = environ.get('SAMPLE')
        activity_ids = (
            self.client.query(
                create_activities_query(
                    athlete_id=self.athlete_id,
                    data_source=self.data_source,
                    data_stream=stream,
                )
            )
            .to_dataframe()["activity_id"]
            .values
        )
        logger.info(f"Extracted {len(activity_ids)} activity ids for {stream}")

        module_strava_json_list = (
            list(
                itertools.islice(
                    self.partial_strava_storage(strava_model=stream).iterdir(),
                    int(sample),
                )
            )
            if sample
            else list(self.partial_strava_storage(strava_model=stream).iterdir())
        )
        if sample:
            logger.info(f"Sampling has been turned on: {sample}")


        filtered_module_strava_json_list = [
            file
            for file in module_strava_json_list
            if file.stem.split("=")[1] not in activity_ids
        ]

        with tqdm_joblib(
                tqdm(desc=f"Processing {stream}", total=len(filtered_module_strava_json_list))
        ):
            result = Parallel(
                n_jobs=int(environ.get("WORKER"))
                if environ.get("WORKER")
                else mp.cpu_count(),
                backend="threading",
            )(
                delayed(self.load_json_into_dataframe)(
                    file=json_file, data_stream=stream
                )
                for json_file in filtered_module_strava_json_list
            )

        # result = [self.load_json_into_dataframe(file=json_file, data_stream=stream) for json_file in filtered_module_strava_json_list]


        dataframes = [result["dataframe"] for result in result]
        metrics = [result["metrics"] for result in result]
        return dataframes, metrics

    @beartype
    def load_json_into_dataframe(
            self, file: GSPath, data_stream: FitnessLLMDataStream
    ) -> dict[str, DataFrame | Metrics]:
        logger.debug("Starting to process %s", file)
        loaded_json = {
            "athlete_id": self.athlete_id,
            "activity_id": file.stem.split("=")[1],
            "data": json.loads(file.read_text()),
        }
        processed_jsons = self.process_json(loaded_json)
        logger.debug("Processed json for %s", file)
        partial_metrics = partial(
            Metrics,
            athlete_id=self.athlete_id,
            activity_id=file.stem.split("=")[1],
            data_source=self.data_source.value,
            data_stream=data_stream,
        )

        if isinstance(processed_jsons, list):
            if isinstance(processed_jsons[0], list):
                logger.debug("Processing multiple jsons for %s", file)
                dataframe = DataFrame(list(itertools.chain(*processed_jsons)))
                return {
                    "dataframe": dataframe,
                    "metrics": partial_metrics(record_count=dataframe.shape[0]),
                }
            logger.debug("Processing single json for %s", file)
            dataframe = DataFrame(processed_jsons)
            return {
                "dataframe": dataframe,
                "metrics": partial_metrics(record_count=dataframe.shape[0]),
            }
        logger.debug("Processing single json for %s", file)
        dataframe = DataFrame(processed_jsons, index=[0])
        return {
            "dataframe": dataframe,
            "metrics": partial_metrics(record_count=dataframe.shape[0]),
        }

    @staticmethod
    @beartype
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
        return {}

    @beartype
    def upsert_to_bigquery(
        self,
        stream: StravaStreams,
        dataframes: list[DataFrame],
        metrics: list[Metrics],
    ):
        timestamp = datetime.now()
        try:
            self.client.load_table_from_dataframe(
                dataframe=dataframes,
                destination=f"dev_strava.{stream}",
                job_config=bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND
                ),
            )
            self.insert_metrics(
                metrics_list=metrics,
                destination="dev_metrics.metrics",
                timestamp=timestamp,
                status=Status.SUCCESS,
            )
        except Exception as e:
            logger.error(f"Error while inserting for {stream.value} for {self.athlete_id}: {e}")
            self.insert_metrics(
                metrics_list=metrics,
                destination="dev_metrics.metrics",
                timestamp=timestamp,
                status=Status.FAILURE,
            )

    @beartype
    def insert_metrics(
            self, metrics_list: list[Metrics], destination: str, timestamp: datetime, status: Status
    ):
        try:
            metrics_list = [
                asdict(metrics.update(bq_insert_timestamp=timestamp, status=status.value))
                for metrics in metrics_list
            ]
            dataframe = DataFrame(metrics_list)
            self.client.load_table_from_dataframe(
                dataframe=dataframe,
                destination=destination,
                job_config=bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND
                ),
            )
        except Exception as e:
            logger.error("Unable to write metrics to BigQuery.")
            raise e
