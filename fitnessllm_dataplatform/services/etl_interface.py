"""ETL Interface for Fitness LLM Data Platform."""

import traceback
from os import environ

from google.cloud import bigquery

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource


class ETLInterface:
    """ETL Interface for Fitness LLM Data Platform."""

    uid: str
    data_source: FitnessLLMDataSource
    service_name: str

    def __init__(self):
        """Initializes ETL Interface."""
        self.client = bigquery.Client()
        self.ENV = environ.get("ENV", "dev")

    def _get_common_fields(self) -> dict:
        """Get a logger with common fields.

        Returns:
            Dict of common logging fields
        """
        fields = {
            "uid": self.uid,
            "data_source": self.data_source,
            "service": self.service_name,
        }
        return fields

    @staticmethod
    def _get_exception_fields(e: Exception) -> dict:
        """Get a logger with exception fields.

        Returns:
            Dict of exception logging fields
        """
        fields = {
            "exception": str(e),
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        return fields
