"""ETL Interface for Strava data."""
import itertools
import json
import tempfile
from datetime import datetime
from enum import EnumType
from functools import partial
from os import environ

import numpy as np
import pandas as pd
from beartype import beartype
from cloudpathlib import GSPath
from google.cloud import bigquery
from joblib import Parallel, delayed
from joblib._multiprocessing_helpers import mp
from pandas import DataFrame
from tqdm import tqdm
from tqdm_joblib import tqdm_joblib

from fitnessllm_dataplatform.entities.dataclasses import Metrics
from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
    Status,
)
from fitnessllm_dataplatform.services.etl_interface import ETLInterface
from fitnessllm_dataplatform.stream.strava.cloud_utils import get_strava_storage_path
from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams
from fitnessllm_dataplatform.stream.strava.entities.queries import (
    create_activities_query,
)
from fitnessllm_dataplatform.stream.strava.etl_utils import execute_etl_func
from fitnessllm_dataplatform.utils.logging_utils import logger
from fitnessllm_dataplatform.utils.task_utils import load_schema_from_json


class BronzeStravaETLInterface(ETLInterface):
    """ETL Interface for Strava data."""

    def __init__(
        self,
        infrastructure_names: EnumType,
        athlete_id: str,
        data_streams: list[str] | None = None,
    ):
        """Initializes Strava ETL Interface."""
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


    @beartype
    def load_json_into_bq(self) -> None:
        """Loads JSONs into BigQuery."""
        try:
            streams = [
                StravaStreams[element.name.upper()]
                for element in self.partial_strava_storage(strava_model=None).iterdir()
            ]
        except KeyError as exc:
            logger.error(
                f"User defined data_streams for Strava not found: {self.data_streams}: {exc}"
            )
            raise exc

        if self.data_streams:
            streams = [
                stream for stream in streams if stream.value in self.data_streams
            ]

        for stream in streams:
            logger.info(f"Loading {stream} for {self.athlete_id}")
            dataframes, metrics = self.convert_stream_json_to_dataframe(stream=stream)
            if dataframes and metrics:
                self.upsert_to_bigquery(
                    stream=stream,
                    dataframes=dataframes,
                    metrics=metrics,
                )
            else:
                logger.info(f"No new data for {stream} for {self.athlete_id}")

    @beartype
    def convert_stream_json_to_dataframe(self, stream: StravaStreams):
        """Converts JSONs to DataFrames."""
        sample = environ.get("SAMPLE")
        activity_ids = (
            self.client.query(
                create_activities_query(
                    env=self.ENV,
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
        if not filtered_module_strava_json_list:
            return [], []
        if int(environ.get("WORKER", 1)) > 1 or environ.get("WORKER") is None:
            with tqdm_joblib(
                tqdm(
                    desc=f"Processing {stream}",
                    total=len(filtered_module_strava_json_list),
                )
            ):
                result = Parallel(
                    n_jobs=int(environ.get("WORKER", 1))
                    if environ.get("WORKER")
                    else mp.cpu_count(),
                    backend="threading",
                )(
                    delayed(self.load_json_into_dataframe)(
                        file=json_file, data_stream=stream
                    )
                    for json_file in filtered_module_strava_json_list
                )
        else:
            result = [
                self.load_json_into_dataframe(file=json_file, data_stream=stream)
                for json_file in filtered_module_strava_json_list
            ]

        dataframes = [result["dataframe"] for result in result]
        metrics = [result["metrics"] for result in result]
        return dataframes, metrics

    @staticmethod
    def clean_column_names(df):
        """Cleans column names."""
        df.columns = df.columns.str.replace(
            r"\.", "_", regex=True
        )  # Replace dot with underscore
        df.columns = df.columns.str.replace(
            r"[^a-zA-Z0-9_]", "", regex=True
        )  # Remove special characters
        df.columns = df.columns.str.strip()  # Remove leading/trailing spaces
        return df

    @staticmethod
    @beartype
    def process_other_json(data_dict: dict) -> DataFrame:
        """Processes JSONs other than activity and athlete summary."""
        data = data_dict["data"]
        data = DataFrame(data={"data": [] if data is None else data})
        data = data.reset_index(inplace=False, drop=True)
        data["index"] = np.arange(1, len(data) + 1)
        data["original_size"] = data_dict["original_size"]
        data["series_type"] = data_dict["series_type"]
        return data

    @beartype
    def load_json_into_dataframe(
        self, file: GSPath, data_stream: FitnessLLMDataStream
    ) -> dict[str, DataFrame | Metrics]:
        """Loads JSON into DataFrame."""
        logger.debug("Starting to process %s", file)
        data_dict = json.loads(file.read_text())
        if isinstance(data_dict, str):
            data_dict = json.loads(data_dict)

        partial_metrics = partial(
            Metrics,
            athlete_id=self.athlete_id,
            activity_id=file.stem.split("=")[1],
            data_source=self.data_source.value,
            data_stream=data_stream,
        )
        # TODO: Turn this into a dictionary with functions
        if data_stream in [StravaStreams.ATHLETE_SUMMARY, StravaStreams.ACTIVITY]:
            df = pd.json_normalize(data_dict)
            if data_stream == StravaStreams.ACTIVITY:
                df = self.clean_column_names(df)
                df.rename(columns={"id": "activity_id"}, inplace=True)
                df["athlete_id"] = df["athlete_id"].astype(str)
                df["activity_id"] = df["activity_id"].astype(str)
            if data_stream == StravaStreams.ATHLETE_SUMMARY:
                df = self.clean_column_names(df)
                df.rename(columns={"id": "athlete_id"}, inplace=True)
                df["athlete_id"] = df["athlete_id"].astype(str)
        else:
            df = self.process_other_json(data_dict)
            df["athlete_id"] = self.athlete_id
            df["activity_id"] = file.stem.split("=")[1]

        df = execute_etl_func(stream=data_stream, df=df)

        return {
            "dataframe": df,
            "metrics": partial_metrics(record_count=df.shape[0]),
        }

    @beartype
    def upsert_to_bigquery(
        self,
        stream: StravaStreams,
        dataframes: list[DataFrame],
        metrics: list[Metrics],
    ) -> None:
        """Upserts DataFrames into BigQuery."""
        timestamp = datetime.now()
        df = pd.concat(dataframes)
        df["metadata_insert_timestamp"] = pd.to_datetime(timestamp)
        try:
            with tempfile.TemporaryDirectory():
                job = self.client.load_table_from_dataframe(
                    dataframe=df,
                    destination=f"{self.client.project}.{self.ENV}_bronze_{self.data_source.value.lower()}.{stream.value}",
                    job_config=bigquery.LoadJobConfig(
                        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                        schema=load_schema_from_json(
                            data_source=self.data_source, data_stream=stream
                        ),
                    ),
                )
                result = job.result()
            if result.state == "DONE":
                self.insert_metrics(
                    metrics_list=metrics,
                    destination=f"{self.client.project}.{self.ENV
                    }_metrics.metrics",
                    timestamp=timestamp,
                    status=Status.SUCCESS,
                )
                return
            raise Exception("Job did not complete successfully")
        except Exception as e:
            logger.error(
                f"Error while inserting for {stream.value} for {self.athlete_id}: {e}"
            )
            self.insert_metrics(
                metrics_list=metrics,
                destination="dev_metrics.metrics",
                timestamp=timestamp,
                status=Status.FAILURE,
            )

    @beartype
    def insert_metrics(
        self,
        metrics_list: list[Metrics],
        destination: str,
        timestamp: datetime,
        status: Status,
    ):
        """Inserts metrics into BigQuery."""
        try:
            metrics_list_converted = [
                metrics.update(
                    bq_insert_timestamp=timestamp, status=status.value
                ).as_dict()
                for metrics in metrics_list
            ]
            dataframe = DataFrame(metrics_list_converted)
            dataframe["bq_insert_timestamp"] = pd.to_datetime(
                dataframe["bq_insert_timestamp"]
            )
            with tempfile.TemporaryDirectory():
                job = self.client.load_table_from_dataframe(
                    dataframe=dataframe,
                    destination=destination,
                    job_config=bigquery.LoadJobConfig(
                        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
                    ),
                )
                result = job.result()
            if result.state != "DONE":
                logger.error("Unable to insert metrics into BigQuery.")
        except Exception as e:
            logger.error("Unable to write metrics to BigQuery.")
            raise e
