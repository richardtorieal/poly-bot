import pytest
import httpx
import respx
import json
from unittest.mock import AsyncMock
from src.data.client import PolymarketClient
from src.strategies.negative_risk import NegativeRiskStrategy
from src.security.config import Settings
from src.security.safety import SafetyManager

@pytest.fixture
def mock_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("PRIVATE_KEY", "0x123")
    monkeypatch.setenv("POLYMARKET_API_KEY", "key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
    settings = Settings(STATE_FILE=str(tmp_path / "state.json"))
    safety = SafetyManager(settings)
    return safety, settings

@pytest.mark.asyncio
@respx.mock
async def test_negative_risk_scan_no_arb(mock_setup):
    safety, mock_settings = mock_setup
    
    # Mock gamma-api.polymarket.com
    respx.get("https://gamma-api.polymarket.com/markets").mock(
        return_value=httpx.Response(200, json=[
            {
                "closed": False,
                "negRiskMarketID": "group1",
                "clobTokenIds": '["t1", "t2"]',
                "slug": "test-slug",
                "events": [{"title": "Test Event", "slug": "test-slug"}]
            }
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
        strategy = NegativeRiskStrategy(client, safety=safety, profit_margin=0.02, polling_interval=0)
        strategy.start_wss = AsyncMock()
        strategy._alert_discord = AsyncMock()
        await strategy.run_iteration()

@pytest.mark.asyncio
@respx.mock
async def test_negative_risk_scan_with_arb(mock_setup, caplog):
    safety, mock_settings = mock_setup
    
    # Mock gamma-api.polymarket.com
    respx.get("https://gamma-api.polymarket.com/markets").mock(
        return_value=httpx.Response(200, json=[
            {
                "closed": False,
                "negRiskMarketID": "group1",
                "clobTokenIds": '["t1", "t2"]',
                "slug": "test-slug",
                "events": [{"title": "Test Event", "slug": "test-slug"}]
            }
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
        strategy = NegativeRiskStrategy(client, safety=safety, profit_margin=0.02, polling_interval=0)
        strategy.start_wss = AsyncMock()
        strategy._alert_discord = AsyncMock()
        await strategy.run_iteration()
        # Verify alert was called
        assert strategy._alert_discord.called
