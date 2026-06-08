from datetime import datetime, timedelta
from typing import Dict
from src.utils.logger import logger
from src.security.config import Settings

class RiskManager:
    """
    Manages global safety switches and drawdown limits.
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self.daily_start_balance = 0.0
        self.current_balance = 0.0
        self.last_reset = datetime.now()
        self.is_kill_switch_active = False

    def check_safety(self) -> bool:
        """
        Main safety check. Returns True if safe to trade.
        """
        if self.is_kill_switch_active:
            logger.error("🛑 KILL SWITCH ACTIVE. Trading blocked.")
            return False

        # Reset daily balance at midnight
        if datetime.now() - self.last_reset > timedelta(days=1):
            logger.info("📅 Daily risk reset.")
            self.daily_start_balance = self.current_balance
            self.last_reset = datetime.now()

        # Check Drawdown
        if self.daily_start_balance > 0:
            drawdown = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
            if drawdown > self.settings.DAILY_DRAWDOWN_LIMIT:
                logger.critical(f"📉 DRAWDOWN LIMIT REACHED ({drawdown*100:.2f}%). Emergency shutdown.")
                self.is_kill_switch_active = True
                return False

        return True

    def update_balance(self, new_balance: float):
        if self.daily_start_balance == 0:
            self.daily_start_balance = new_balance
        self.current_balance = new_balance
        logger.debug(f"💰 Balance updated: ${new_balance:.2f}")

    def activate_kill_switch(self, reason: str):
        logger.critical(f"🚨 MANUAL KILL SWITCH ACTIVATED: {reason}")
        self.is_kill_switch_active = True
