"""Tests for configuration management."""
import os
from pathlib import Path
from unittest.mock import patch

from dashboard_viewer.config import Settings


def test_default_settings():
    """Test that default settings are loaded correctly."""
    # Explicitly disable .env file loading for this test
    settings = Settings(_env_file=None)

    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.image_url == "https://ha.zaks.io/local/dashboard-art.png"
    assert settings.homeassistant_url == "https://ha.zaks.io"
    assert settings.homeassistant_token is None
    assert settings.dev_mode is False
    assert settings.vite_base_path == ""
    assert settings.has_homeassistant_auth is False


def test_env_var_override():
    """Test that environment variables override defaults."""
    with patch.dict(os.environ, {
        "HOST": "127.0.0.1",
        "PORT": "9000",
        "IMAGE_URL": "https://example.com/image.png",
        "HOMEASSISTANT_TOKEN": "test-token",
        "DEV_MODE": "true",
        "VITE_BASE_PATH": "/dashboard"
    }):
        settings = Settings()

        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.image_url == "https://example.com/image.png"
        assert settings.homeassistant_token == "test-token"
        assert settings.dev_mode is True
        assert settings.vite_base_path == "/dashboard"
        assert settings.has_homeassistant_auth is True


def test_env_file_loading(tmp_path):
    """Test that .env file is loaded correctly."""
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text("""
HOST=localhost
PORT=8080
IMAGE_URL=https://test.com/test.png
HOMEASSISTANT_TOKEN=secret-token
DEV_MODE=true
VITE_BASE_PATH=/api/dashboard
""")

    # Change to temp directory and load settings
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        settings = Settings(_env_file=".env")

        assert settings.host == "localhost"
        assert settings.port == 8080
        assert settings.image_url == "https://test.com/test.png"
        assert settings.homeassistant_token == "secret-token"
        assert settings.dev_mode is True
        assert settings.vite_base_path == "/api/dashboard"
    finally:
        os.chdir(original_cwd)


def test_case_insensitive():
    """Test that environment variables are case insensitive."""
    with patch.dict(os.environ, {
        "host": "192.168.1.1",
        "PORT": "7000",
        "Image_URL": "https://mixed-case.com/img.png"
    }):
        settings = Settings()

        assert settings.host == "192.168.1.1"
        assert settings.port == 7000
        assert settings.image_url == "https://mixed-case.com/img.png"


def test_vite_base_path_configuration():
    """Test VITE_BASE_PATH configuration for subpath deployment."""
    # Test with various base path values
    test_cases = [
        ("", ""),  # Empty string (root deployment)
        ("/dashboard", "/dashboard"),  # Simple subpath
        ("/api/v1/dashboard", "/api/v1/dashboard"),  # Nested subpath
        ("dashboard", "dashboard"),  # Without leading slash
    ]

    for env_value, expected_value in test_cases:
        with patch.dict(os.environ, {"VITE_BASE_PATH": env_value}):
            settings = Settings()
            assert settings.vite_base_path == expected_value


def test_backend_exports():
    """Test that backend exports work correctly with VITE_BASE_PATH."""

    with patch.dict(os.environ, {"VITE_BASE_PATH": "/test-path"}):
        # Reload settings to pick up env var
        new_settings = Settings()
        assert new_settings.vite_base_path == "/test-path"


def test_fastapi_root_path_configuration():
    """Test that FastAPI app correctly uses VITE_BASE_PATH for root_path."""
    # Test with empty base path
    with patch.dict(os.environ, {"VITE_BASE_PATH": ""}):
        from dashboard_viewer.config import BASE_PATH, Settings
        settings = Settings()
        assert settings.vite_base_path == ""
        assert BASE_PATH == ""

    # Test with subpath
    with patch.dict(os.environ, {"VITE_BASE_PATH": "/dashboard"}):
        import importlib

        import dashboard_viewer.config
        importlib.reload(dashboard_viewer.config)

        from dashboard_viewer.config import BASE_PATH, Settings
        settings = Settings()
        assert settings.vite_base_path == "/dashboard"
        assert BASE_PATH == "/dashboard"


def test_subpath_trailing_slash_handling():
    """Test that subpath configuration handles trailing slashes correctly."""
    test_cases = [
        ("/dashboard", "/dashboard"),  # No trailing slash
        ("/dashboard/", "/dashboard/"),  # With trailing slash
        ("dashboard", "dashboard"),  # No leading slash
        ("", ""),  # Empty string
    ]

    for input_path, expected_path in test_cases:
        with patch.dict(os.environ, {"VITE_BASE_PATH": input_path}):
            settings = Settings()
            assert settings.vite_base_path == expected_path
