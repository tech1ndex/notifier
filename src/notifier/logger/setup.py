import sys

from loguru import logger


def setup_logger():
    logger.remove()
    logger.add(
        sink=sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
        level="INFO",
    )
    return logger
