import sys
import os
import logging
from loguru import logger

class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logger(log_level="INFO"):
    """
    Configures loguru logger.
    """
    logger.remove()
    
    # Standard Loguru Console
    logger.add(sys.stderr, level=log_level)
    
    # Sink to standard logging so pytest caplog can see it
    logger.add(lambda msg: logging.log(logging.WARNING, msg), level="WARNING")
    logger.add(lambda msg: logging.log(logging.INFO, msg), level="INFO")

    return logger

setup_logger()
