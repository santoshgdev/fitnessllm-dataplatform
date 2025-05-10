"""Logging utilities."""

import json
import logging
from datetime import datetime
from logging import Logger
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fitnessllm_shared.entities.constants import TIMEZONE


class StructuredLogger:
    """Custom logger that adds structured logging capabilities."""

    def __init__(self, name: str | None = None, level: int = logging.DEBUG) -> None:
        """Initialize the structured logger.

        Args:
            name: Name of the logger
            level: Logging level
        """
        self.logger = setup_logger(name, level)
        self.name = name or "root"

    def _format_log(
        self,
        level: str,
        message: str,
        data_source: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Format log entry with structured data."""
        log_data = {
            "level": level,
            "message": message,
            "service": self.name,
            "timestamp": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
        }

        if data_source:
            log_data["data_source"] = data_source
        if user_id:
            log_data["user_id"] = user_id

        # Add any additional fields
        log_data.update(kwargs)

        return log_data

    def info(
        self,
        message: str,
        data_source: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log info level message with structured data."""
        log_data = self._format_log("INFO", message, data_source, user_id, **kwargs)
        self.logger.info(json.dumps(log_data))

    def error(
        self,
        message: str,
        data_source: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log error level message with structured data."""
        log_data = self._format_log("ERROR", message, data_source, user_id, **kwargs)
        self.logger.error(json.dumps(log_data))

    def warning(
        self,
        message: str,
        data_source: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log warning level message with structured data."""
        log_data = self._format_log("WARNING", message, data_source, user_id, **kwargs)
        self.logger.warning(json.dumps(log_data))

    def debug(
        self,
        message: str,
        data_source: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log debug level message with structured data."""
        log_data = self._format_log("DEBUG", message, data_source, user_id, **kwargs)
        self.logger.debug(json.dumps(log_data))


def setup_logger(name: str | None = None, level: int = logging.DEBUG) -> Logger:
    """Sets up a logger with a console handler.

    Args:
        name (str): Name of the logger.
        level (int): Logging level (e.g., logging.DEBUG, logging.INFO).

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("stravalib").setLevel(logging.WARNING)
    logging.getLogger("google.auth._default").setLevel(logging.WARNING)

    # Prevent adding duplicate handlers if this function is called multiple times
    if logger.hasHandlers():
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


# Create default logger instance
logger = setup_logger()

# Create default structured logger instance
structured_logger = StructuredLogger()
