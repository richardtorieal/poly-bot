from src.utils.logger import logger
import os

def test_logger_initialization():
    logger.info("Testing logger initialization")
    assert True

def test_log_file_creation():
    logger.info("Forcing file creation")
    log_dir = "logs"
    files = os.listdir(log_dir)
    assert len(files) > 0
    assert any(f.startswith("polybot_") for f in files)
