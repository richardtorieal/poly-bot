from abc import ABC, abstractmethod
from typing import Any, Dict, List
from src.utils.logger import logger

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Ensures a consistent interface for the Strategy Engine.
    """
    def __init__(self, name: str):
        self.name = name
        self.is_active = False
        logger.info(f"Initialized strategy: {self.name}")

    @abstractmethod
    async def start(self):
        """Starts the strategy execution loop."""
        self.is_active = True
        logger.info(f"Starting execution for {self.name}")

    @abstractmethod
    async def stop(self):
        """Safely stops the strategy execution loop."""
        self.is_active = False
        logger.info(f"Stopping execution for {self.name}")

    @abstractmethod
    async def tick(self):
        """A single iteration of the strategy logic."""
        pass

    def __repr__(self):
        return f"<Strategy: {self.name} (Active: {self.is_active})>"
