import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.websocket_client import WebSocketClient

@pytest.mark.asyncio
async def test_websocket_initialization():
    client = WebSocketClient(uri="wss://test.uri")
    assert client.uri == "wss://test.uri"
    assert client.is_running is False

@pytest.mark.asyncio
async def test_websocket_subscribe():
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_ws = AsyncMock()
        
        # Define empty async iterator to prevent infinite loops when iterating mock
        async def mock_aiter():
            return
            yield
            
        mock_ws.__aiter__ = mock_aiter
        mock_connect.return_value = mock_ws
        
        client = WebSocketClient()
        try:
            await client.connect()
            await client.subscribe(["token1", "token2"])
            
            # Verify subscription message format matching real implementation
            sent_msg = json.loads(mock_ws.send.call_args[0][0])
            assert sent_msg["type"] == "MARKET"
            assert "token1" in sent_msg["assets_ids"]
        finally:
            await client.close()
