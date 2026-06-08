from abc import ABC, abstractmethod
from src.data.client import PolymarketClient
from src.utils.logger import logger
from src.security.safety import SafetyManager
from typing import Dict, Any

class BaseStrategy(ABC):
    """
    Abstract Base Class for all trading strategies with safety integration.
    """
    def __init__(self, client: PolymarketClient, safety: SafetyManager, name: str):
        self.client = client
        self.safety = safety
        self.name = name
        self.is_running = False

    @abstractmethod
    async def run_iteration(self):
        """
        Executes a single iteration of the strategy.
        """
        pass

    async def start(self):
        logger.info(f"Starting strategy: {self.name}")
        self.is_running = True
        try:
            while self.is_running:
                # 1. Safety Check (Assuming $100 baseline for bootstrap)
                if not self.safety.is_safe_to_trade(current_portfolio_value=100.0):
                    logger.warning(f"Strategy {self.name} paused by Safety Manager.")
                    await asyncio.sleep(60)
                    continue

                # 2. Execute Iteration
                await self.run_iteration()
        except Exception as e:
            logger.error(f"Strategy {self.name} failed: {e}")
            self.is_running = False

    def stop(self):
        logger.info(f"Stopping strategy: {self.name}")
        self.is_running = False
