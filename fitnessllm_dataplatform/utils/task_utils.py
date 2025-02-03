"""Module for used task utilities."""
import os
from enum import Enum


def load_into_env_vars(options: dict):
    """Loads a given dict with options into environmental variables.

    Args:
        options: dict with options to load
    """
    for key, value in options.items():
        if type(value) in [str, int, float, bool]:
            os.environ[key] = value

def get_enum_values_from_list(enum: list[Enum]):
    return [member.value for member in enum]
