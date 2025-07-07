from loguru import logger


def setup_logger():
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
        level="INFO"
    )

    return logger