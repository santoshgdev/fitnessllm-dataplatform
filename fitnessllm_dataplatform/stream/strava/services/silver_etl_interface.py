"""Module for Strava Silver ETL interface."""

import os
import pathlib

from tqdm import tqdm
from utils.logging_utils import structured_logger

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource
from fitnessllm_dataplatform.services.etl_interface import ETLInterface
from fitnessllm_dataplatform.utils.query_utils import get_delete_query, get_insert_query


class SilverStravaETLInterface(ETLInterface):
    """Silver ETL interface for Strava data."""

    def __init__(self, uid: str, athlete_id: str):
        """Initializes Strava ETL Interface."""
        super().__init__()
        self.uid = uid
        self.data_source = FitnessLLMDataSource.STRAVA
        self.athlete_id = athlete_id

    def task_handler(self):
        """Task handler for Strava ETL."""
        path = "fitnessllm_dataplatform/stream/strava/schemas/silver/sql"
        list_of_queries = os.listdir(path)

        parameters = {
            "schema": f"{self.ENV}_bronze_{self.data_source.value.lower()}",
            "athlete_id": self.athlete_id,
        }

        for query in tqdm(list_of_queries):
            target_destination = f"{self.ENV}_silver_{self.data_source.value.lower()}.{query.split('.')[0]}"
            query_path = pathlib.Path(path, query)

            delete_query = get_delete_query(
                target_table=target_destination, parameters=parameters
            )
            delete_job = self.client.query(delete_query)
            delete_job.result()
            if delete_job.state != "DONE" and delete_job.error is not None:
                structured_logger.error(
                    message=f"Query {delete_query} failed with error {delete_job.error}",
                    uid=self.athlete_id,
                    data_source=self.data_source.value,
                    service="silver_etl",
                )
                continue
            structured_logger.debug(
                message=f"Query {delete_query} successfully deleted {delete_job.num_dml_affected_rows}",
                uid=self.uid,
                data_source=self.data_source.value.lower(),
                service="silver_etl",
            )
            insert_query = get_insert_query(
                target_table=target_destination,
                query_path=query_path,
                parameters=parameters,
            )
            insert_job = self.client.query(insert_query)
            insert_job.result()
            if insert_job.state != "DONE" and insert_job.error is not None:
                structured_logger.error(
                    message="Query failed with error",
                    query=insert_query,
                    uid=self.uid,
                    data_source=self.data_source.value,
                    service="silver_etl",
                )
                continue
            structured_logger.debug(
                message=f"Query successfully inserted {insert_job.num_dml_affected_rows} rows",
                uid=self.uid,
                data_source=self.data_source.value,
                query=insert_query,
                service="silver_etl",
            )
