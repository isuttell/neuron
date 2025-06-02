"""Tests for configuration management."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

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
    assert settings.has_homeassistant_auth is False


def test_env_var_override():
    """Test that environment variables override defaults."""
    with patch.dict(os.environ, {
        "HOST": "127.0.0.1",
        "PORT": "9000",
        "IMAGE_URL": "https://example.com/image.png",
        "HOMEASSISTANT_TOKEN": "test-token",
        "DEV_MODE": "true"
    }):
        settings = Settings()

        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.image_url == "https://example.com/image.png"
        assert settings.homeassistant_token == "test-token"
        assert settings.dev_mode is True
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
