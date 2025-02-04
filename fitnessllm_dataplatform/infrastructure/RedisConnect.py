"""Redis Connection Module."""
import json

import redis

from fitnessllm_dataplatform.utils.cloud_utils import get_secret
from fitnessllm_dataplatform.utils.logging_utils import logger
from beartype import beartype

class RedisConnect:
    """Infrastructure Redis Connect."""

    def __init__(self):
        """Init function."""
        pass

    def open_connection(self):
        """Open Redis connection."""
        redis_info = get_secret("redis_dev")
        self.interface = redis.Redis(
            host=redis_info["host"],
            port=redis_info["port"],
            username=redis_info["user"],
            password=redis_info["pw"],
        )
        logger.debug("Opened Redis connection.")

    def close_connection(self):
        """Close Redis connection."""
        self.interface.close()
        logger.debug("Closed redis connection.")

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
        self.open_connection()
        try:
            self.interface.set(name=key, value=json.dumps(value))
            if ttl:
                self.interface.setex(name=key, value=json.dumps(value), time=ttl)
                logger.debug(f"Wrote key with ttl {ttl}")
            logger.debug(f"Set {key} to redis")

        except redis.RedisError as exc:
            logger.error(f"Failed to set key '{key}': {exc}")
        finally:
            self.close_connection()
            return

    @beartype
    def read_redis(self, key: str) -> dict:
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
                raise redis.RedisError(f"Failed to get key '{key}'; does not exist")
            else:
                return json.loads(value)

        except redis.RedisError as exc:
            raise redis.RedisError(f"Failed to get key '{key}': {exc}")
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
        except redis.RedisError as exc:
            logger.error(f"Failed to get key '{key}' ttl: {exc}")
            return None
        finally:
            self.close_connection()
