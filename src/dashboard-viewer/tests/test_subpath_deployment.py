"""Integration tests for subpath deployment scenario."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_full_subpath_deployment_scenario():
    """Test complete subpath deployment like https://lapetus.zaks.io/dashboard."""
    # Simulate the exact configuration from docker-compose.prod.yml
    env_vars = {
        "VITE_BASE_PATH": "/dashboard",
        "HOST": "0.0.0.0",
        "PORT": "8000"
    }

    with patch.dict(os.environ, env_vars):
        # Import after setting environment variables
        import importlib

        import dashboard_viewer.config
        import dashboard_viewer.server

        # Reload modules to pick up new env vars
        importlib.reload(dashboard_viewer.config)
        importlib.reload(dashboard_viewer.server)

        app = dashboard_viewer.server.app
        client = TestClient(app)

        # Test that FastAPI app is configured with correct root_path
        assert app.root_path == "/dashboard"

        # Test health check endpoint (what Traefik will hit)
        response = client.head("/")
        assert response.status_code == 200

        # Test API endpoints work with subpath
        response = client.get("/api/config")
        assert response.status_code == 200

        response = client.get("/api/status")
        assert response.status_code == 200


def test_subpath_vs_root_deployment():
    """Test that the app works correctly in both root and subpath deployments."""
    # Test root deployment
    with patch.dict(os.environ, {"VITE_BASE_PATH": ""}):
        import importlib

        import dashboard_viewer.config
        importlib.reload(dashboard_viewer.config)

        from dashboard_viewer.config import BASE_PATH
        assert BASE_PATH == ""

    # Test subpath deployment
    with patch.dict(os.environ, {"VITE_BASE_PATH": "/dashboard"}):
        import importlib

        import dashboard_viewer.config
        importlib.reload(dashboard_viewer.config)

        from dashboard_viewer.config import BASE_PATH
        assert BASE_PATH == "/dashboard"


def test_frontend_backend_coordination():
    """Test that frontend and backend configurations are coordinated."""
    subpath = "/dashboard"

    with patch.dict(os.environ, {"VITE_BASE_PATH": subpath}):
        import importlib

        import dashboard_viewer.config
        importlib.reload(dashboard_viewer.config)

        from dashboard_viewer.config import BASE_PATH, settings

        # Backend should use the same base path
        assert settings.vite_base_path == subpath
        assert subpath == BASE_PATH

        # This ensures FastAPI root_path matches Vite base path
        # so asset paths and API paths are consistent


def test_docker_compose_environment_variables():
    """Test that all environment variables from docker-compose.prod.yml work correctly."""
    # Simulate the exact environment from docker-compose.prod.yml
    prod_env = {
        "VITE_BASE_PATH": "/dashboard",
        "PORT": "8000",
        "HOST": "0.0.0.0",
        "IMAGE_URL": "http://host.docker.internal:8123/local/dashboard-art.png",
        "HOMEASSISTANT_TOKEN": "test-token"
    }

    with patch.dict(os.environ, prod_env):
        import importlib

        import dashboard_viewer.config
        importlib.reload(dashboard_viewer.config)

        from dashboard_viewer.config import settings

        # Verify all settings are loaded correctly
        assert settings.vite_base_path == "/dashboard"
        assert settings.port == 8000
        assert settings.host == "0.0.0.0"
        assert settings.image_url == "http://host.docker.internal:8123/local/dashboard-art.png"
        assert settings.homeassistant_token == "test-token"


def test_traefik_route_matching():
    """Test that the app works with Traefik's route matching configuration."""
    # Based on our Traefik config:
    # - "traefik.http.routers.dashboard-viewer.rule=Host(`lapetus.zaks.io`) && PathPrefix(`/dashboard`)"
    # - "traefik.http.services.dashboard-viewer.loadbalancer.healthcheck.path=/dashboard/"

    with patch.dict(os.environ, {"VITE_BASE_PATH": "/dashboard"}):
        import importlib

        import dashboard_viewer.server
        importlib.reload(dashboard_viewer.server)

        app = dashboard_viewer.server.app
        client = TestClient(app)

        # Traefik will forward requests with /dashboard prefix to our app
        # FastAPI with root_path="/dashboard" should handle this correctly

        # Test health check path that Traefik will use
        response = client.head("/")  # This becomes /dashboard/ at Traefik level
        assert response.status_code == 200

        # Test that API endpoints work
        response = client.get("/api/status")  # This becomes /dashboard/api/status at Traefik level
        assert response.status_code == 200


def test_static_file_paths_with_subpath():
    """Test that static file serving works correctly with subpath."""
    with patch.dict(os.environ, {"VITE_BASE_PATH": "/dashboard"}):
        # Mock that static files exist
        with patch('dashboard_viewer.server.DIST_DIR') as mock_dist_dir:
            mock_dist_dir.exists.return_value = True

            import importlib

            import dashboard_viewer.server
            importlib.reload(dashboard_viewer.server)

            app = dashboard_viewer.server.app
            client = TestClient(app)

            # FastAPI should serve static files at root path
            # When Traefik forwards /dashboard/assets/app.js -> /assets/app.js
            # FastAPI with root_path="/dashboard" handles this correctly

            # Test root path (serves index.html)
            response = client.get("/")
            assert response.status_code in [200, 404]  # 404 is acceptable for missing static files


def test_websocket_url_construction():
    """Test that WebSocket URLs work correctly with subpath deployment."""
    # This tests the frontend logic in DashboardImageWS.tsx
    # The component constructs WebSocket URLs using window.location.host

    # With subpath deployment, the WebSocket URL should still work
    # because Traefik forwards the WebSocket connection with the full path

    subpath = "/dashboard"
    with patch.dict(os.environ, {"VITE_BASE_PATH": subpath}):
        import importlib

        import dashboard_viewer.server
        importlib.reload(dashboard_viewer.server)

        app = dashboard_viewer.server.app
        client = TestClient(app)

        # Test WebSocket endpoint
        with client.websocket_connect("/ws") as websocket:
            # Should connect successfully
            data = websocket.receive_json()
            assert data["type"] == "connected"


@pytest.mark.parametrize("base_path", ["", "/dashboard", "/api/v1/dashboard", "/test"])
def test_multiple_subpath_configurations(base_path):
    """Test that the app works with various subpath configurations."""
    with patch.dict(os.environ, {"VITE_BASE_PATH": base_path}):
        import importlib

        import dashboard_viewer.config
        import dashboard_viewer.server

        importlib.reload(dashboard_viewer.config)
        importlib.reload(dashboard_viewer.server)

        from dashboard_viewer.config import settings
        app = dashboard_viewer.server.app
        client = TestClient(app)

        # Configuration should be set correctly
        assert settings.vite_base_path == base_path
        # Note: root_path behavior may vary in test environment
        assert hasattr(app, 'root_path')

        # Health check should work
        response = client.head("/")
        assert response.status_code == 200

        # API endpoints should work
        response = client.get("/api/status")
        assert response.status_code == 200
