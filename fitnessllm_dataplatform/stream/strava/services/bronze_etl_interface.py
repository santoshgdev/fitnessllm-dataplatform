"""ETL Interface for Strava data."""

import itertools
import json
import tempfile
import traceback
from datetime import datetime
from enum import EnumType
from functools import partial
from os import environ
from typing import Optional

import numpy as np
import pandas as pd
from beartype import beartype
from cloudpathlib import GSPath
from fitnessllm_shared.logger_utils import structured_logger
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
from fitnessllm_dataplatform.utils.task_utils import load_schema_from_json


class BronzeStravaETLInterface(ETLInterface):
    """ETL Interface for Strava data.

    This class provides methods to extract, transform, and load Strava data
    into BigQuery. It handles various data streams, processes JSON files,
    and manages metrics for the operations performed.

    Attributes:
        SERVICE_NAME (str): The name of the service, used for logging and identification.
        uid (str): A unique identifier for the ETL process.
        data_source (FitnessLLMDataSource): The data source being processed (e.g., Strava).
        athlete_id (str): The ID of the athlete whose data is being processed.
        data_streams (Optional[list[str]]): A list of data streams to process, if specified.
        InfrastructureNames (EnumType): Infrastructure configuration details.
        partial_strava_storage (Callable): A partial function to get the storage path for Strava data.
    """

    SERVICE_NAME = "bronze_etl"

    def __init__(
        self,
        uid: str,
        infrastructure_names: EnumType,
        athlete_id: str,
        data_streams: Optional[list[str]] = None,
    ):
        """Initializes the Strava ETL Interface.

        This constructor sets up the necessary attributes for the ETL process,
        including a unique identifier, infrastructure configuration, athlete ID,
        and optional data streams to process.

        Args:
            uid (str): A unique identifier for the ETL process.
            infrastructure_names (EnumType): Infrastructure configuration details.
            athlete_id (str): The ID of the athlete whose data is being processed.
            data_streams (Optional[list[str]]): A list of data streams to process, if specified.
        """
        super().__init__()
        self.uid = uid
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
        """Loads JSON files into BigQuery.

        This method identifies the data streams to be processed, logs the operation,
        and converts JSON files into DataFrames. It then upserts the resulting data
        into BigQuery. If no new data is found, a warning is logged.

        Raises:
            KeyError: If the specified data streams are not found.
        """
        try:
            streams = [
                StravaStreams[element.name.upper()]
                for element in self.partial_strava_storage(strava_model=None).iterdir()
            ]
        except KeyError as exc:
            structured_logger.error(
                message="User defined data_streams not found",
                uid=self.uid,
                data_source=self.data_source.value,
                exception=exc,
                traceback=traceback.format_exc(),
                service=self.SERVICE_NAME,
            )
            raise exc

        if self.data_streams:
            streams = [
                stream for stream in streams if stream.value in self.data_streams
            ]

        for stream in streams:
            structured_logger.info(
                message="Loading stream for athlete_id",
                athlete_id=self.athlete_id,
                stream=stream.value,
                uid=self.uid,
                data_source=self.data_source.value,
                service=self.SERVICE_NAME,
            )
            dataframes, metrics = self.convert_stream_json_to_dataframe(stream=stream)
            if dataframes and metrics:
                self.upsert_to_bigquery(
                    stream=stream,
                    dataframes=dataframes,
                    metrics=metrics,
                )
            else:
                structured_logger.warning(
                    message="No new data",
                    uid=self.uid,
                    data_source=self.data_source.value,
                    service=self.SERVICE_NAME,
                )

    @beartype
    def convert_stream_json_to_dataframe(self, stream: StravaStreams):
        """Converts JSON files to DataFrames.

        This method processes JSON files associated with a specific data stream,
        filters out already processed activity IDs, and converts the remaining
        JSON files into Pandas DataFrames. It also generates associated metrics
        for the processed data.

        Args:
            stream (StravaStreams): The data stream being processed (e.g., activity or athlete summary).

        Returns:
            tuple: A tuple containing:
                - dataframes (list[DataFrame]): A list of DataFrames created from the JSON files.
                - metrics (list[Metrics]): A list of metrics associated with the processed data.

        Raises:
            KeyError: If the data stream is not found in the storage path.
        """
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
        structured_logger.info(
            message="Extracted activity ids for stream",
            activity_id_count=len(activity_ids),
            stream=stream.value,
            uid=self.uid,
            data_source=self.data_source.value,
            service=self.SERVICE_NAME,
        )

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
            structured_logger.debug(
                message=f"Sampling has been turned on {sample}",
                uid=self.uid,
                data_source=self.data_source.value,
                service=self.SERVICE_NAME,
            )

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
                    n_jobs=(
                        int(environ.get("WORKER", 1))
                        if environ.get("WORKER")
                        else mp.cpu_count()
                    ),
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
    @beartype
    def clean_column_names(df: DataFrame) -> DataFrame:
        """Cleans column names in a DataFrame.

        This method standardizes column names by replacing dots with underscores,
        removing special characters, and stripping leading/trailing spaces.

        Args:
            df (DataFrame): The Pandas DataFrame whose column names need to be cleaned.

        Returns:
            DataFrame: A Pandas DataFrame with cleaned column names.
        """
        df.columns = df.columns.str.replace(r"\.", "_", regex=True)
        df.columns = df.columns.str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
        df.columns = df.columns.str.strip()
        return df

    @staticmethod
    @beartype
    def process_other_json(data_dict: dict) -> DataFrame:
        """Processes JSON data that is not related to activity or athlete summary.

        This method takes a dictionary containing JSON data, extracts relevant fields,
        and converts it into a Pandas DataFrame. Additional metadata such as index,
        original size, and series type are added to the DataFrame.

        Args:
            data_dict (dict): A dictionary containing the JSON data to be processed.
                              Expected keys include 'data', 'original_size', and 'series_type'.

        Returns:
            DataFrame: A Pandas DataFrame containing the processed data with added metadata.
        """
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
        """Loads a JSON file into a DataFrame and generates associated metrics.

        This method reads a JSON file from a given path, processes its content
        based on the specified data stream, and returns a dictionary containing
        the resulting DataFrame and metrics.

        Args:
            file (GSPath): The path to the JSON file to be loaded.
            data_stream (FitnessLLMDataStream): The type of data stream being processed
                                                (e.g., activity or athlete summary).

        Returns:
            dict[str, DataFrame | Metrics]: A dictionary containing:
                - 'dataframe': The processed DataFrame.
                - 'metrics': Metrics associated with the processed data.

        Raises:
            Exception: If the JSON file cannot be read or processed.
        """
        structured_logger.debug(
            message=f"Starting to process {file}",
            uid=self.uid,
            data_source=self.data_source.value,
        )
        data_dict = json.loads(file.read_text())
        if isinstance(data_dict, str):
            data_dict = json.loads(data_dict)

        partial_metrics = partial(
            Metrics,
            athlete_id=self.athlete_id,
            activity_id=file.stem.split("=")[1],
            data_source=self.data_source,
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
        """Upserts DataFrames into BigQuery.

        This method combines multiple DataFrames into one, adds a metadata timestamp,
        and inserts the resulting DataFrame into a BigQuery table. It also logs metrics
        about the operation. If the insertion fails, an error is logged, and the metrics
        are updated with a failure status.

        Args:
            stream (StravaStreams): The data stream being processed (e.g., activity or athlete summary).
            dataframes (list[DataFrame]): A list of DataFrames to be upserted into BigQuery.
            metrics (list[Metrics]): A list of metrics associated with the data being upserted.

        Raises:
            Exception: If the BigQuery insertion job does not complete successfully or
                       if any other error occurs during the process.
        """
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
                    destination=f"{self.client.project}.{self.ENV}_metrics.metrics",
                    timestamp=timestamp,
                    status=Status.SUCCESS,
                )
                return
            raise Exception("Job did not complete successfully")
        except Exception as e:
            structured_logger.error(
                message=f"Error while inserting {stream.value} into BigQuery for {self.athlete_id}",
                uid=self.uid,
                data_source=self.data_source.value,
                exception=str(e),
                traceback=traceback.format_exc(),
                service=self.SERVICE_NAME,
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
        """Inserts metrics into BigQuery.

        This method takes a list of metrics, updates them with a timestamp and status,
        and inserts them into a specified BigQuery table. If the insertion fails,
        an error is logged and the exception is raised.

        Args:
            metrics_list (list[Metrics]): A list of metrics to be inserted into BigQuery.
            destination (str): The BigQuery table where the metrics will be inserted.
            timestamp (datetime): The timestamp to associate with the metrics.
            status (Status): The status to assign to the metrics (e.g., SUCCESS or FAILURE).

        Raises:
            Exception: If the metrics insertion job does not complete successfully or
                       if any other error occurs during the process.
        """
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
                structured_logger.error(
                    message="Unable to insert metrics into BigQuery.",
                    athlete_id=self.athlete_id,
                    uid=self.uid,
                    data_source=self.data_source.value,
                    service=self.SERVICE_NAME,
                )
                raise Exception("Metrics insertion job did not complete successfully")
        except Exception as e:
            structured_logger.error(
                message="Unable to write metrics to BigQuery",
                uid=self.uid,
                data_source=self.data_source.value,
                exception=str(e),
                traceback=traceback.format_exc(),
                service=self.SERVICE_NAME,
            )
            raise e
