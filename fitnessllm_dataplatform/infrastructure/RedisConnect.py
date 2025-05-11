"""Redis Connection Module."""

import json

import redis
from beartype import beartype
from fitnessllm_shared.logging_utils import structured_logger

from fitnessllm_dataplatform.utils.cloud_utils import get_secret


class RedisConnect:
    """Infrastructure Redis Connect."""

    def __init__(self):
        """Init function."""

    def open_connection(self):
        """Open Redis connection."""
        redis_info = get_secret("redis_dev")
        self.interface = redis.Redis(
            host=redis_info["host"],
            port=redis_info["port"],
            username=redis_info["user"],
            password=redis_info["pw"],
        )
        structured_logger.debug(message="Opened Redis connection.")

    def close_connection(self):
        """Close Redis connection."""
        self.interface.close()
        structured_logger.debug(message="Closed redis connection.")

    @beartype
    def write_redis(self, key: str, value: dict, ttl: None | int = None) -> None:
        """Write key-value to redis db specified in interface.

        Args:
            key: str representing key name.
            value: dict representing value.
            ttl: int representing ttl in seconds.

        Raises:
            RedisError
        """
        try:
            self.open_connection()
            self.interface.set(name=key, value=json.dumps(value))
            if ttl:
                self.interface.setex(name=key, value=json.dumps(value), time=ttl)
                structured_logger.debug(message=f"Wrote key with ttl {ttl}")
            structured_logger.debug(message=f"Set {key} to redis")
        except redis.exceptions.AuthenticationError as exc:
            structured_logger.error(
                message="Failed to authenticate to Redis", exception=exc
            )
            raise
        except redis.RedisError as exc:
            structured_logger.error(f"Failed to set key '{key}': {exc}")
        finally:
            if hasattr(self, "interface"):
                self.close_connection()
            return

    @beartype
    def read_redis(self, key: str) -> dict | None:
        """Read from redis interface given a key.

        Args:
            key: str representing key name

        Returns:
            Either dict or None depending on if key is available

        Raises:
            RedisError
        """
        self.open_connection()
        try:
            value = self.interface.get(key)
            if value is None:
                return value
            return json.loads(value)
        except redis.exceptions.AuthenticationError as exc:
            structured_logger.error(f"Failed to authenticate to Redis: {exc}")
            raise
        except redis.RedisError:
            structured_logger.debug(f"Failed to get key '{key}'; does not exist")
            return None
        finally:
            self.close_connection()

    @beartype
    def get_ttl(self, key: str) -> int | None:
        """Get TTL for particular key in Redis.

        Args:
            key: str representing key name

        Returns:
            The TTL in seconds.

        Raises:
            RedisError
        """
        self.open_connection()
        try:
            return self.interface.ttl(key)
        except redis.exceptions.AuthenticationError as exc:
            structured_logger.error(f"Failed to authenticate to Redis: {exc}")
            raise
        except redis.RedisError as exc:
            structured_logger.error(f"Failed to get key '{key}' ttl: {exc}")
            raise
        finally:
            self.close_connection()
