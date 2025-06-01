"""Tests for the dashboard viewer server."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

from dashboard_viewer.server import app, get_js_hash, PollingState


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


def test_get_js_hash():
    """Test JavaScript hash extraction from index.html."""
    # Mock index.html content
    mock_content = '''<!doctype html>
<html>
<head>
    <script type="module" crossorigin src="/assets/index-ABC123def.js"></script>
</head>
</html>'''

    with patch('pathlib.Path.read_text', return_value=mock_content):
        with patch('pathlib.Path.exists', return_value=True):
            hash_value = get_js_hash()
            assert hash_value == "ABC123def"


def test_get_js_hash_file_not_exists():
    """Test hash extraction when index.html doesn't exist."""
    with patch('pathlib.Path.exists', return_value=False):
        hash_value = get_js_hash()
        assert hash_value is None


def test_get_js_hash_no_match():
    """Test hash extraction when no script tag is found."""
    mock_content = '''<!doctype html>
<html>
<head>
    <title>Test</title>
</head>
</html>'''

    with patch('pathlib.Path.read_text', return_value=mock_content):
        with patch('pathlib.Path.exists', return_value=True):
            hash_value = get_js_hash()
            assert hash_value is None


def test_api_config(client):
    """Test the /api/config endpoint."""
    response = client.get("/api/config")
    assert response.status_code == 200

    data = response.json()
    assert "image_url" in data
    assert "server" in data
    assert "poll_interval" in data
    assert "websocket_url" in data


def test_api_status(client):
    """Test the /api/status endpoint."""
    response = client.get("/api/status")
    assert response.status_code == 200

    data = response.json()
    assert "is_polling" in data
    assert "current_etag" in data
    assert "last_check" in data
    assert "connected_clients" in data
    assert "js_hash" in data


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection and initial message."""
    from dashboard_viewer.server import ConnectionManager

    # Create a new manager for isolated testing
    manager = ConnectionManager()

    # Mock WebSocket with async methods
    mock_websocket = MagicMock()
    mock_websocket.accept = MagicMock(return_value=asyncio.Future())
    mock_websocket.accept.return_value.set_result(None)
    mock_websocket.send_json = MagicMock()

    # Test connection
    await manager.connect(mock_websocket)

    assert mock_websocket in manager.active_connections
    mock_websocket.accept.assert_called_once()


def test_polling_state_initialization():
    """Test PollingState class initialization."""
    state = PollingState()

    assert state.current_etag is None
    assert state.last_check is None
    assert state.poll_interval == 10  # Should be 10 seconds
    assert state.is_polling is False
    assert state.cached_image is None
    assert state.cached_content_type is None
    assert isinstance(state.cached_headers, dict)
    assert state.js_hash is None


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """Test ConnectionManager broadcast functionality."""
    from dashboard_viewer.server import ConnectionManager

    manager = ConnectionManager()

    # Mock WebSocket connections
    ws1 = MagicMock()
    ws2 = MagicMock()
    ws1.send_text = MagicMock()
    ws2.send_text = MagicMock()

    manager.active_connections.add(ws1)
    manager.active_connections.add(ws2)

    # Test broadcast
    message = {"type": "test", "data": "hello"}
    await manager.broadcast(message)

    # Both connections should receive the message
    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()


def test_test_etag_endpoint(client):
    """Test the /test-etag endpoint for ETag behavior."""
    # First request should return 200 with content
    response = client.get("/test-etag")
    assert response.status_code == 200
    etag = response.headers.get("etag")
    assert etag == '"test-etag-123"'

    # Second request with matching ETag should return 304
    response = client.get("/test-etag", headers={"if-none-match": etag})
    assert response.status_code == 304
    assert response.headers.get("etag") == etag
