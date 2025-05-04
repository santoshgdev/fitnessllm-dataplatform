import logging

from fitnessllm_dataplatform.utils.logging_utils import setup_logger


def test_setup_logger_default():
    logger = setup_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG
    assert logger.hasHandlers()
    has_stream_handler = any(
        isinstance(handler, logging.StreamHandler) for handler in logger.handlers
    )
    assert has_stream_handler, "Logger does not have a StreamHandler"


def test_setup_logger_with_name_and_level():
    logger = setup_logger(name="test_logger", level=logging.INFO)
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO
    assert logger.hasHandlers()
