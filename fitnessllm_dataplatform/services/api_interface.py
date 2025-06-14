"""API Interface for FitnessLLM Data Platform."""

import traceback

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource


class APIInterface:
    """API Interface for FitnessLLM Data Platform."""

    uid: str
    data_source: FitnessLLMDataSource
    service_name: str = "ingest"

    def __init__(self):
        """Initializes API Interface."""
        pass

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
