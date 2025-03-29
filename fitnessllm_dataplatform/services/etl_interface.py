"""ETL Interface for Fitness LLM Data Platform."""
from os import environ

from google.cloud import bigquery


class ETLInterface:
    """ETL Interface for Fitness LLM Data Platform."""

    def __init__(self):
        """Initializes ETL Interface."""
        self.client = bigquery.Client()
        self.ENV = environ.get("ENV", "dev")
