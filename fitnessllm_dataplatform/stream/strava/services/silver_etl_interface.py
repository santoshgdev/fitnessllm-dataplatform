import os
import pathlib

from google.cloud import bigquery

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource
from fitnessllm_dataplatform.services.etl_interface import ETLInterface

from fitnessllm_dataplatform.utils.query_utils import get_parameterized_query, \
    get_transaction_insert_query


class SilverStravaETLInterface(ETLInterface):
    """Silver ETL interface for Strava data."""

    def __init__(self,
                 athlete_id: str):
        """Initializes Strava ETL Interface."""
        super().__init__()
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

        for query in list_of_queries:
            target_destination = f"{self.ENV}_silver_{self.data_source.value.lower()}.{query.split('.')[0]}"
            query_path = pathlib.Path(path, query)

            out = get_transaction_insert_query(target_table=target_destination,
                                               query_path=query_path,
                                               parameters=parameters)

            result = self.client.query(out).result()
