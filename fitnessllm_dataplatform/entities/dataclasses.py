"""Dataclasses for the entities in the FitnessLLM Data Platform."""
from dataclasses import asdict, dataclass
from datetime import datetime

from beartype.typing import Optional

from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
)
from fitnessllm_dataplatform.utils.task_utils import dataclass_convertor


@dataclass
class Metrics:
    """A dataclass for storing metrics data from various data sources.

    Attributes:
        athlete_id: Unique identifier for the athlete.
        activity_id: Unique identifier for the activity.
        data_source: Source of the data (e.g., Strava).
        data_stream: Type of data stream (e.g., heartrate, cadence).
        record_count: Number of records in the data stream.
        status: Optional status of the data processing.
        bq_insert_timestamp: Optional timestamp of BigQuery insertion.
    """

    athlete_id: str
    activity_id: str
    data_source: FitnessLLMDataSource
    data_stream: FitnessLLMDataStream
    record_count: int
    status: Optional[str] = None
    bq_insert_timestamp: Optional[datetime] = None

    def as_dict(self):
        """Converts dataclass to dict."""
        return asdict(
            self, dict_factory=lambda x: {k: dataclass_convertor(v) for k, v in x}
        )

    def update(self, **kwargs):
        """Updates dataclass attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"{key} is not a valid attribute of Metrics")
        return self
