"""Module for Strava Silver ETL interface."""

import os
import pathlib

from beartype import beartype
from fitnessllm_shared.logger_utils import structured_logger
from tqdm import tqdm

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource
from fitnessllm_dataplatform.services.etl_interface import ETLInterface
from fitnessllm_dataplatform.utils.query_utils import get_delete_query, get_insert_query


class SilverStravaETLInterface(ETLInterface):
    """Silver ETL interface for Strava data.

    This class provides methods to handle the extraction, transformation,
    and loading (ETL) of Strava data into the Silver layer of the data platform.

    Attributes:
        SERVICE_NAME (str): The name of the service, used for logging and identification.
    """

    SERVICE_NAME = "silver_etl"

    def __init__(self, uid: str, athlete_id: str):
        """Initializes the Silver Strava ETL Interface.

        This constructor sets up the necessary attributes for the ETL process,
        including a unique identifier and the athlete ID.

        Args:
            uid (str): A unique identifier for the ETL process.
            athlete_id (str): The ID of the athlete whose data is being processed.
        """
        super().__init__()
        self.uid = uid
        self.data_source = FitnessLLMDataSource.STRAVA
        self.athlete_id = athlete_id

    @beartype
    def _get_common_field(self) -> dict[str, str]:
        fields = super()._get_common_fields()
        fields.update({"athlete_id": self.athlete_id})
        return fields

    def task_handler(self):
        """Handles the execution of ETL tasks for Strava data.

        This method processes SQL queries located in the specified directory,
        executes delete and insert operations on the target tables in the Silver
        layer, and logs the results of each operation. It ensures that data is
        properly transformed and loaded into the Silver layer.

        Raises:
            Exception: If any query execution fails or encounters an error.
        """
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
                    message="Query failed with error",
                    query=delete_query,
                    error=delete_job.error,
                    uid=self.athlete_id,
                    data_source=self.data_source.value,
                    service=self.SERVICE_NAME,
                )
                continue
            structured_logger.debug(
                message="Query successfully deleted rows",
                query=delete_query,
                num_deleted=delete_job.num_dml_affected_rows,
                uid=self.uid,
                data_source=self.data_source.value,
                service=self.SERVICE_NAME,
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
                    service=self.SERVICE_NAME,
                )
                continue
            structured_logger.debug(
                message="Query successfully inserted rows",
                num_inserted=insert_job.num_dml_affected_rows,
                uid=self.uid,
                data_source=self.data_source.value,
                query=insert_query,
                service=self.SERVICE_NAME,
            )
