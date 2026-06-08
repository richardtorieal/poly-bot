import pytest
import httpx
import respx
from src.data.client import PolymarketClient
from src.security.config import Settings

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "0x123")
    monkeypatch.setenv("POLYMARKET_API_KEY", "key")
    monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
    return Settings()

@pytest.mark.asyncio
@respx.mock
async def test_client_get_markets(mock_settings):
    respx.get("https://clob.polymarket.com/markets").mock(
        return_value=httpx.Response(200, json={"markets": [{"id": "m1"}]})
    )
    
    async with PolymarketClient(mock_settings) as client:
        markets = await client.get_markets()
        assert markets["markets"][0]["id"] == "m1"

@pytest.mark.asyncio
@respx.mock
async def test_client_get_price(mock_settings):
    respx.get("https://clob.polymarket.com/price").mock(
        return_value=httpx.Response(200, json={"price": "0.50"})
    )
    
    async with PolymarketClient(mock_settings) as client:
        price = await client.get_price("token1")
        assert price["price"] == "0.50"
