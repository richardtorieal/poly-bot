import pytest
import httpx
import respx
from src.data.client import PolymarketClient
from src.strategies.negative_risk import NegativeRiskStrategy
from src.security.config import Settings
from src.security.safety import SafetyManager

from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "0x123")
    monkeypatch.setenv("POLYMARKET_API_KEY", "key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
    monkeypatch.setenv("FINNHUB_API_KEY", "key") # needed to avoid ValidationError if environment is missing it
    monkeypatch.setenv("DISCORD_TOKEN", "") # clear it to avoid actual Discord POSTs
    return Settings()

@pytest.mark.asyncio
@respx.mock
@patch("src.strategies.negative_risk.NegativeRiskStrategy.start_wss", new_callable=AsyncMock)
@patch("src.strategies.negative_risk.NegativeRiskStrategy._alert_discord", new_callable=AsyncMock)
async def test_negative_risk_scan_no_arb(mock_alert_discord, mock_start_wss, mock_settings):
    # Mock market with 2 tokens
    respx.get("https://gamma-api.polymarket.com/markets").mock(
        return_value=httpx.Response(200, json=[
            {"id": "m1", "question": "Test?", "clobTokenIds": '["t1", "t2"]'}
        ])
    )
    # Mock prices: 0.55 + 0.55 = 1.10 (No arb)
    respx.get("https://clob.polymarket.com/price", params={"token_id": "t1", "side": "buy"}).mock(
        return_value=httpx.Response(200, json={"price": "0.55"})
    )
    respx.get("https://clob.polymarket.com/price", params={"token_id": "t2", "side": "buy"}).mock(
        return_value=httpx.Response(200, json={"price": "0.55"})
    )

    async with PolymarketClient(mock_settings) as client:
        safety = SafetyManager(mock_settings)
        strategy = NegativeRiskStrategy(client, safety, profit_margin=0.02, polling_interval=0)
        await strategy.run_iteration()

@pytest.mark.asyncio
@respx.mock
@patch("src.strategies.negative_risk.NegativeRiskStrategy.start_wss", new_callable=AsyncMock)
@patch("src.strategies.negative_risk.NegativeRiskStrategy._alert_discord", new_callable=AsyncMock)
async def test_negative_risk_scan_with_arb(mock_alert_discord, mock_start_wss, mock_settings, caplog):
    # Mock market
    respx.get("https://gamma-api.polymarket.com/markets").mock(
        return_value=httpx.Response(200, json=[
            {"id": "m1", "question": "Test?", "clobTokenIds": '["t1", "t2"]'}
        ])
    )
    # Mock prices: 0.45 + 0.45 = 0.90 (Arb! < 0.98 margin)
    respx.get("https://clob.polymarket.com/price", params={"token_id": "t1", "side": "buy"}).mock(
        return_value=httpx.Response(200, json={"price": "0.45"})
    )
    respx.get("https://clob.polymarket.com/price", params={"token_id": "t2", "side": "buy"}).mock(
        return_value=httpx.Response(200, json={"price": "0.45"})
    )

    async with PolymarketClient(mock_settings) as client:
        safety = SafetyManager(mock_settings)
        strategy = NegativeRiskStrategy(client, safety, profit_margin=0.02, polling_interval=0)
        await strategy.run_iteration()
