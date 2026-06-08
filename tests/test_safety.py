import pytest
import os
import json
from src.security.safety import SafetyManager
from src.security.config import Settings

@pytest.fixture
def safety_setup(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("PRIVATE_KEY", "0x123")
    monkeypatch.setenv("POLYMARKET_API_KEY", "key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
    
    settings = Settings(STATE_FILE=str(state_file))
    return SafetyManager(settings), settings

def test_global_kill_switch(safety_setup):
    safety, settings = safety_setup
    settings.GLOBAL_KILL_SWITCH = True
    assert safety.is_safe_to_trade(100.0) is False

def test_daily_drawdown_limit(safety_setup):
    safety, settings = safety_setup
    # Set limit to 5% of 100 ($5)
    settings.DAILY_DRAWDOWN_LIMIT = 0.05
    
    # Record a $6 loss
    safety.record_trade(-6.0)
    assert safety.is_safe_to_trade(100.0) is False

def test_safe_trading_condition(safety_setup):
    safety, settings = safety_setup
    # Small profit, should be safe
    safety.record_trade(1.0)
    assert safety.is_safe_to_trade(100.0) is True
