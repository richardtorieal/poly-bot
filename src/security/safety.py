import json
import os
from datetime import datetime
from src.utils.logger import logger
from src.security.config import Settings

class SafetyManager:
    """
    Enforces risk management rules and provides proximity alerts.
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self.state_file = settings.STATE_FILE
        self._initialize_state()

    def _initialize_state(self):
        if not os.path.exists(self.state_file):
            state = {
                "last_reset": datetime.now().date().isoformat(),
                "daily_pnl": 0.0,
                "is_halted": False
            }
            self._save_state(state)

    def _get_state(self):
        with open(self.state_file, 'r') as f:
            state = json.load(f)
        return state

    def _save_state(self, state):
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=4)

    def is_safe_to_trade(self, current_portfolio_value: float) -> bool:
        if self.settings.GLOBAL_KILL_SWITCH:
            return False

        state = self._get_state()
        limit_amount = current_portfolio_value * self.settings.DAILY_DRAWDOWN_LIMIT # 15%
        
        # PROXIMITY ALERT (Fixed at 10% of portfolio)
        warning_threshold = current_portfolio_value * 0.10
        if state["daily_pnl"] < -warning_threshold and state["daily_pnl"] > -limit_amount:
            logger.critical(f"⚠️ PROXIMITY ALERT: Drawdown is at ${abs(state['daily_pnl']):.2f}. "
                            f"Approaching 15% safety limit (${limit_amount:.2f})!")

        # HARD LIMIT
        if state["daily_pnl"] < -limit_amount:
            logger.error(f"❌ DAILY DRAWDOWN LIMIT REACHED. Trading halted.")
            return False

        return True

    def record_trade(self, pnl: float):
        state = self._get_state()
        state["daily_pnl"] += pnl
        self._save_state(state)
