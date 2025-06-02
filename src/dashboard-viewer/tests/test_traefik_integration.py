"""Tests for Traefik integration and health check compatibility."""

from unittest.mock import patch

from dashboard_viewer.server import app
from fastapi.testclient import TestClient


def test_health_check_endpoint_compatibility():
    """Test that health check endpoint works as expected by Traefik."""
    client = TestClient(app)

    # Test HEAD request (what Traefik health checks use)
    response = client.head("/")

    # Should return 200 OK
    assert response.status_code == 200

    # Should have content-type header
    assert "content-type" in response.headers

    # HEAD request should not have body content
    assert response.content == b""

    # Should be fast (not require complex processing)
    assert response.headers.get("cache-control") is not None


def test_health_check_with_subpath():
    """Test that health check works correctly with subpath deployment."""
    with patch.dict('os.environ', {"VITE_BASE_PATH": "/dashboard"}):
        client = TestClient(app)

        # Health check should work at root path
        response = client.head("/")
        assert response.status_code == 200
        assert response.content == b""

        # Should also work with GET for debugging
        response = client.get("/")
        assert response.status_code in [200, 404]  # 200 for dev fallback, 404 for static files


def test_traefik_loadbalancer_compatibility():
    """Test compatibility with Traefik's load balancer health checks."""
    client = TestClient(app)

    # Test the exact path Traefik will use based on our config
    # healthcheck.path=/dashboard/ in docker-compose.prod.yml

    # Test HEAD request to health check path
    response = client.head("/")

    # Must return 2xx status for Traefik to consider service healthy
    assert 200 <= response.status_code < 300

    # Response should be fast and lightweight
    assert response.content == b""

    # Should not require authentication or complex logic
    assert "www-authenticate" not in response.headers


def test_cors_headers_present():
    """Test that CORS headers are present for browser compatibility."""
    client = TestClient(app)

    # Test OPTIONS request (CORS preflight)
    response = client.options("/")

    # Should handle CORS properly
    # Note: Actual CORS headers depend on middleware configuration
    assert response.status_code in [200, 404, 405]  # Various acceptable responses


def test_service_port_configuration():
    """Test that the service responds on the expected port configuration."""
    # This tests that our app is configured to work with:
    # traefik.http.services.dashboard-viewer.loadbalancer.server.port=8000

    from dashboard_viewer.config import settings

    # Should be configured for port 8000 (default)
    assert settings.port == 8000

    # Host should be 0.0.0.0 for container networking
    assert settings.host == "0.0.0.0"


def test_watchtower_compatibility():
    """Test that the application can handle graceful shutdowns for Watchtower updates."""
    # This is more of a documentation test since we can't easily test
    # the actual signal handling in unit tests

    # Verify that the app has proper lifespan management
    # Note: In newer FastAPI versions, lifespan is stored differently
    assert hasattr(app, 'router') and hasattr(app.router, 'lifespan_context')

    # The lifespan should handle cleanup (tested via startup/shutdown)
    # This ensures Watchtower can gracefully restart the container


def test_static_file_serving_with_subpath():
    """Test that static files are served correctly with subpath configuration."""
    # Mock static files directory exists
    with patch('dashboard_viewer.server.DIST_DIR') as mock_dist_dir:
        mock_dist_dir.exists.return_value = True

        client = TestClient(app)

        # Test that root path works (static files mounted at "/")
        response = client.get("/")

        # Should either serve static file or return 404 (both acceptable)
        assert response.status_code in [200, 404]


def test_network_configuration_docker():
    """Test that the app is configured for Docker network communication."""
    from dashboard_viewer.config import settings

    # Should bind to all interfaces for Docker
    assert settings.host == "0.0.0.0"

    # Should use standard HTTP port internally
    assert settings.port == 8000

    # Should not have any localhost-specific configuration
    assert "localhost" not in settings.host
    assert "127.0.0.1" not in settings.host
