import pytest
import httpx
import respx
from src.data.news_client import NewsClient
from src.strategies.news_trigger import NewsTriggerStrategy
from src.security.safety import SafetyManager
from src.security.config import Settings

@pytest.fixture
def mock_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "0x123")
    monkeypatch.setenv("POLYMARKET_API_KEY", "key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
    
    settings = Settings(STATE_FILE=str(tmp_path / "state.json"))
    safety = SafetyManager(settings)
    return safety, settings

@pytest.mark.asyncio
@respx.mock
async def test_news_client_fetch(mock_setup):
    respx.get("https://cryptopanic.com/api/v1/posts/").mock(
        return_value=httpx.Response(200, json={"results": [{"id": 1, "title": "Bitcoin is mooning"}]})
    )
    
    client = NewsClient()
    news = await client.fetch_latest_news()
    assert len(news) == 1
    assert news[0]["title"] == "Bitcoin is mooning"
    await client.close()

from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@respx.mock
async def test_news_trigger_match(mock_setup):
    safety, settings = mock_setup
    
    # Mock News API
    respx.get("https://cryptopanic.com/api/v1/posts/").mock(
        return_value=httpx.Response(200, json={"results": [{"id": 1, "title": "New bitcoin ETF approved"}]})
    )
    
    # Mock Polymarket (not used yet but client needs it)
    client = None 
    news_client = NewsClient()
    
    strategy = NewsTriggerStrategy(client, safety, news_client)
    # run iteration once
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await strategy.run_iteration()
    
    state = safety._get_state()
    assert state["daily_pnl"] >= 1.0 # At least one trigger
    await news_client.close()
