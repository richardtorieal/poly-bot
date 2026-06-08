import os
from src.security.config import Settings
import pytest
from pydantic import ValidationError

def test_config_validation_fail():
    # Test missing fields
    with pytest.raises(ValidationError):
        Settings()

def test_config_validation_success(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "0x123")
    monkeypatch.setenv("POLYMARKET_API_KEY", "key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
    
    config = Settings()
    assert config.POLYMARKET_API_KEY == "key"
    assert config.PRIVATE_KEY.get_secret_value() == "0x123"
