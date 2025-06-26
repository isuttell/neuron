"""Tests for app controller."""

from unittest.mock import patch

import pytest
from quart import Quart

from neuron_server.api import app as neuron_app
from neuron_server.llms.tools import get_protected_tool_sets


@pytest.fixture
def app() -> Quart:
    """Return the Quart app for testing."""
    return neuron_app


@pytest.mark.asyncio
class TestAppController:
    """Test cases for app controller endpoints."""

    async def test_get_config_structure(self, app):
        """Test that config endpoint returns expected structure."""
        async with app.test_client() as client:
            response = await client.get("/api/app/config")
            assert response.status_code == 200

            data = await response.get_json()
            assert isinstance(data, dict)

            # Check required fields
            assert "sidebar_image" in data
            assert "api" in data
            assert "auth0" in data
            assert "protectedToolSets" in data

            # Check API structure
            api_config = data["api"]
            assert api_config["baseUrl"] == "/api"
            assert api_config["wsEndpoint"] == "/ws"

            # Check auth0 structure
            auth0_config = data["auth0"]
            assert "domain" in auth0_config
            assert "clientId" in auth0_config
            assert "audience" in auth0_config

    async def test_get_config_protected_tool_sets(self, app):
        """Test that config includes protected tool sets."""
        async with app.test_client() as client:
            response = await client.get("/api/app/config")
            assert response.status_code == 200

            data = await response.get_json()
            protected_tool_sets = data["protectedToolSets"]

            # Should match the current protected tool sets
            expected_protected_sets = get_protected_tool_sets()
            assert protected_tool_sets == expected_protected_sets

            # Check specific tool sets we know are protected
            assert "homeassistant" in protected_tool_sets
            assert "kepler" in protected_tool_sets
            assert protected_tool_sets["homeassistant"] == "tool-homeassistant"
            assert protected_tool_sets["kepler"] == "tool-kepler"

    async def test_get_config_with_sidebar_image(self, app):
        """Test config endpoint with mocked sidebar image."""
        # Cache is already mocked in conftest.py to return None by default
        # which is handled by the config endpoint
        async with app.test_client() as client:
            response = await client.get("/api/app/config")
            assert response.status_code == 200

            data = await response.get_json()
            # Default return should be None from mocked cache
            assert data["sidebar_image"] is None

    @patch("neuron_server.controllers.app_controller.get_protected_tool_sets")
    async def test_get_config_calls_protected_tool_sets(
        self, mock_get_protected_sets, app
    ):
        """Test that config endpoint calls get_protected_tool_sets function."""
        mock_protected_sets = {"test_tool": "test-role"}
        mock_get_protected_sets.return_value = mock_protected_sets

        async with app.test_client() as client:
            response = await client.get("/api/app/config")
            assert response.status_code == 200

            data = await response.get_json()
            assert data["protectedToolSets"] == mock_protected_sets
            mock_get_protected_sets.assert_called_once()

    async def test_get_config_response_types(self, app):
        """Test that config response has correct data types."""
        async with app.test_client() as client:
            response = await client.get("/api/app/config")
            assert response.status_code == 200

            data = await response.get_json()

            # Check data types
            assert data["sidebar_image"] is None or isinstance(
                data["sidebar_image"], str
            )
            assert isinstance(data["api"], dict)
            assert isinstance(data["auth0"], dict)
            assert isinstance(data["protectedToolSets"], dict)

            # Check that protectedToolSets values are strings (role names)
            for tool_set, role in data["protectedToolSets"].items():
                assert isinstance(tool_set, str)
                assert isinstance(role, str)
                assert role.startswith("tool-")  # Role naming convention

    async def test_get_config_consistency(self, app):
        """Test that multiple calls return consistent data."""
        async with app.test_client() as client:
            response1 = await client.get("/api/app/config")
            response2 = await client.get("/api/app/config")

            assert response1.status_code == 200
            assert response2.status_code == 200

            data1 = await response1.get_json()
            data2 = await response2.get_json()

            # Protected tool sets should be consistent
            assert data1["protectedToolSets"] == data2["protectedToolSets"]

            # API config should be consistent
            assert data1["api"] == data2["api"]
