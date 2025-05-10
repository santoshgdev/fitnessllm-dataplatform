"""Enums for the FitnessLLM Data Platform."""

from enum import Enum


class DynamicEnum(Enum):
    """A blank enum that adds members via initialization function."""

    pass

    @classmethod
    def from_dict(cls, data):
        """Dynamically add members to the Enum from a dictionary."""
        return Enum(value=cls.__name__, names=list(data.items()))


class FitnessLLMDataStream(Enum):
    """Data streams for the FitnessLLM Data Platform."""

    pass


class FitnessLLMDataSource(Enum):
    """Data sources for the FitnessLLM Data Platform."""

    STRAVA = "STRAVA"


class Status(Enum):
    """Statuses for the FitnessLLM Data Platform."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
