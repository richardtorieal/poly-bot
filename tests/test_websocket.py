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
        mock_connect.return_value = mock_ws
        
        client = WebSocketClient()
        await client.connect()
        await client.subscribe(["token1", "token2"])
        
        # Verify subscription message format
        sent_msg = json.loads(mock_ws.send.call_args[0][0])
        assert sent_msg["type"] == "subscribe"
        assert "token1" in sent_msg["assets"]
