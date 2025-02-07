"""API Interface for FitnessLLM Data Platform."""
from abc import abstractmethod


class APIInterface:
    """API Interface for FitnessLLM Data Platform."""

    def __init__(self):
        """Initializes API Interface."""
        pass

    @abstractmethod
    def refresh_access_token_at_expiration(self):
        """Refreshes access token at expiration."""
        pass

    @abstractmethod
    def write_refreshed_access_token_to_redis(self):
        """Writes refreshed access token to Redis."""
        pass
