from enum import Enum


class DynamicEnum(Enum):
    """A blank enum that adds members via initialization function."""

    pass

    @classmethod
    def from_dict(cls, data):
        """Dynamically add members to the Enum from a dictionary."""
        return Enum(value=cls.__name__, names=list(data.items()))


class FitnessLLMDataStream(Enum):
    pass


class FitnessLLMDataSource(Enum):
    STRAVA = "STRAVA"


class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
