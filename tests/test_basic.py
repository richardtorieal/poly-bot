import pytest
from src.utils.logger import logger
from src.utils.config import settings
from src.strategies.base_strategy import BaseStrategy

def test_logger_init():
    logger.info("Testing logger initialization")
    assert logger is not None

def test_config_defaults():
    assert settings.max_daily_loss == 5.0
    assert settings.default_strategy == "negative_risk"

class MockStrategy(BaseStrategy):
    async def start(self): await super().start()
    async def stop(self): await super().stop()
    async def tick(self): pass

@pytest.mark.asyncio
async def test_base_strategy():
    strat = MockStrategy("Mock")
    assert strat.name == "Mock"
    assert not strat.is_active
    await strat.start()
    assert strat.is_active
    await strat.stop()
    assert not strat.is_active
