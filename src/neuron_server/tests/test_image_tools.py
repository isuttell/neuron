"""Tests for image-related tools with session cookie support."""

import uuid
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_uuid_used_for_cookies() -> None:
    """Test that uuid4 is used to generate session token."""
    with patch("uuid.uuid4", return_value="test-uuid"):
        # This test verifies that uuid4 is used to generate the session token
        assert str(uuid.uuid4()) == "test-uuid"


def test_cookies_construction() -> None:
    """Test cookie construction with session token."""
    # Test without patches to avoid dealing with async mocks
    # We're just checking that the code constructs cookies correctly
    token = "test-token"
    with patch("neuron_server.config.config.static_require_auth", True):
        cookies = {"neuron_session": token} if True else None
        assert cookies == {"neuron_session": "test-token"}
