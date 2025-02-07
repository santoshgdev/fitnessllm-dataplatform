from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

from fitnessllm_dataplatform.entities.enums import (
    FitnessLLMDataSource,
    FitnessLLMDataStream,
)
from fitnessllm_dataplatform.utils.task_utils import dataclass_convertor


@dataclass
class Metrics:
    athlete_id: str
    activity_id: str
    data_source: FitnessLLMDataSource
    data_stream: FitnessLLMDataStream
    record_count: int
    status: Optional[str] = None
    bq_insert_timestamp: Optional[datetime] = None

    def as_dict(self):
        return asdict(
            self, dict_factory=lambda x: {k: dataclass_convertor(v) for k, v in x}
        )

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"{key} is not a valid attribute of Metrics")
        return self
