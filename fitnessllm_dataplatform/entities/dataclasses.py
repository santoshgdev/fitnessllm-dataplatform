from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Metrics:
    athlete_id: str
    activity_id: str
    data_source: str
    data_stream: str
    record_count: int
    status: Optional[str] = None
    bq_insert_timestamp: Optional[datetime] = None

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"{key} is not a valid attribute of Metrics")
        return self