import logging
import sys

from fitnessllm_dataplatform.utils.logging_utils import setup_logger


def test_setup_logger():
    """Test for setting up a logger."""
    logger = setup_logger()
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 4
    assert logger.handlers[0].level == 0
    assert (
        logger.handlers[0].formatter._fmt
        == "%(levelname)-8s %(name)s:%(filename)s:%(lineno)d %(message)s"
    )
    assert logger.handlers[0].stream == sys.stdout
    assert logger.handlers[0].stream.name == "<stdout>"
    assert logger.handlers[0].stream.encoding == "UTF-8"
    assert logger.handlers[0].stream.errors == "strict"
    assert logger.handlers[0].stream.isatty()


def test_setup_logger_has_handlers():
    logger = setup_logger("test_logger")
    assert logger.hasHandlers()
