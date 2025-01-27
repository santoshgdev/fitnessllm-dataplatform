"""Logging utilities."""
import logging
from logging import Logger


def setup_logger(name: str | None = None, level: int = logging.DEBUG) -> Logger:
    """Sets up a logger with a console handler.

    Args:
        name (str): Name of the logger.
        level (int): Logging level git a(e.g., logging.DEBUG, logging.INFO).

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("stravalib").setLevel(logging.WARNING)

    # Prevent adding duplicate handlers if this function is called multiple times
    if logger.hasHandlers():
        return logger

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Create a formatter and set it for the handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
