import pytest
from src.security.risk_manager import RiskManager
from src.security.config import Settings

@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "0x123")
    monkeypatch.setenv("POLYMARKET_API_KEY", "key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
    s = Settings()
    s.DAILY_DRAWDOWN_LIMIT = 0.05 # 5%
    return s

def test_risk_manager_safe_initial(settings):
    rm = RiskManager(settings)
    rm.update_balance(100.0)
    assert rm.check_safety() is True

def test_risk_manager_drawdown_trigger(settings):
    rm = RiskManager(settings)
    rm.update_balance(100.0)
    # Lose 6%
    rm.update_balance(93.9)
    assert rm.check_safety() is False
    assert rm.is_kill_switch_active is True

def test_risk_manager_manual_kill(settings):
    rm = RiskManager(settings)
    rm.activate_kill_switch("User intervention")
    assert rm.check_safety() is False
