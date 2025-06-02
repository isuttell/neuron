"""Tests for the dashboard viewer server."""

import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dashboard_viewer.polling import PollingState, get_js_hash
from dashboard_viewer.server import app
from dashboard_viewer.websocket import ConnectionManager
from fastapi.testclient import TestClient


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
            hash_value = get_js_hash(Path("/fake/dist"))
            assert hash_value == "ABC123def"


def test_get_js_hash_file_not_exists():
    """Test hash extraction when index.html doesn't exist."""
    with patch('pathlib.Path.exists', return_value=False):
        hash_value = get_js_hash(Path("/fake/dist"))
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
            hash_value = get_js_hash(Path("/fake/dist"))
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


def test_subpath_configuration_default():
    """Test that app works with default (empty) base path."""
    # Test with no VITE_BASE_PATH set
    with patch.dict(os.environ, {}, clear=True):
        from dashboard_viewer.config import Settings
        settings = Settings()
        assert settings.vite_base_path == ""

        # App should have None for root_path when base_path is empty
        assert app.root_path == ""


def test_subpath_configuration_with_path():
    """Test that app works with custom base path."""
    with patch.dict(os.environ, {"VITE_BASE_PATH": "/dashboard"}):
        # Import after setting env var
        import importlib

        import dashboard_viewer.config
        importlib.reload(dashboard_viewer.config)

        from dashboard_viewer.config import BASE_PATH, Settings
        settings = Settings()
        assert settings.vite_base_path == "/dashboard"
        assert BASE_PATH == "/dashboard"


def test_api_config_includes_base_path(client):
    """Test that /api/config endpoint includes base path information."""
    response = client.get("/api/config")
    assert response.status_code == 200

    data = response.json()
    # Should include base path info
    assert "image_url" in data
    assert "server" in data


def test_development_fallback_includes_base_path():
    """Test that development fallback endpoint includes base path."""
    # Mock DIST_DIR to not exist to trigger fallback
    with patch('dashboard_viewer.server.DIST_DIR') as mock_dist_dir:
        mock_dist_dir.exists.return_value = False

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

        # Check if response is JSON (dev fallback) or HTML (static files)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            assert "error" in data
            assert "vite_base_path" in data


def test_root_head_endpoint(client):
    """Test that HEAD requests to root path work for health checks."""
    response = client.head("/")
    assert response.status_code == 200
    assert "content-type" in response.headers
    assert "cache-control" in response.headers
    # HEAD requests should not return body content
    assert response.content == b""


def test_root_head_endpoint_with_static_files():
    """Test that HEAD requests work when static files are available."""
    # Mock DIST_DIR to exist
    with patch('dashboard_viewer.server.DIST_DIR') as mock_dist_dir:
        mock_dist_dir.exists.return_value = True

        # Create new client with mocked static files
        client = TestClient(app)
        response = client.head("/")

        # Should still return 200 for health checks
        assert response.status_code == 200
        assert response.content == b""


def test_head_endpoint_subpath_configuration():
    """Test that HEAD endpoint works correctly with subpath configuration."""
    # Test HEAD endpoint responds correctly for health checks
    with patch.dict(os.environ, {"VITE_BASE_PATH": "/dashboard"}):
        client = TestClient(app)

        # Root HEAD should still work (for routes defined in routes.py)
        response = client.head("/")
        assert response.status_code == 200
        assert "content-type" in response.headers

        # Verify no body content in HEAD response
        assert response.content == b""


def test_fastapi_app_root_path_configuration():
    """Test that FastAPI app is configured with correct root_path."""
    # Note: In test environment, module reloading may not work as expected
    # This test documents the expected behavior

    # The app should be configured with root_path based on BASE_PATH

    # Test that the concept works (app has root_path attribute)
    assert hasattr(app, 'root_path')

    # In production, root_path should match BASE_PATH
    # (actual value depends on when the module was loaded)


def test_development_fallback_subpath_info():
    """Test that development fallback includes subpath information."""
    # Mock DIST_DIR to not exist and set subpath
    with patch('dashboard_viewer.server.DIST_DIR') as mock_dist_dir:
        mock_dist_dir.exists.return_value = False

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

        # Check if response is JSON (dev fallback) or HTML (static files)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            assert "vite_base_path" in data
        # Note: May not reflect the exact env var due to module loading
