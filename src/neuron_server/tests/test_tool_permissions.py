"""Tests for tool permission validation functions."""

import pytest
from werkzeug.exceptions import BadRequest, Forbidden

from neuron_server.controllers.personality_controller import (
    validate_tool_set_permissions,
)
from neuron_server.llms.tools import (
    get_available_tool_sets,
    get_missing_tool_permissions,
    get_protected_tool_sets,
    validate_tool_set_keys,
)


class TestToolSetFunctions:
    """Test cases for tool set utility functions."""

    def test_get_available_tool_sets(self):
        """Test that get_available_tool_sets returns valid list."""
        tool_sets = get_available_tool_sets()

        assert isinstance(tool_sets, list)
        assert len(tool_sets) > 0

        # Check that known tool sets are included
        assert "homeassistant" in tool_sets
        assert "kepler" in tool_sets
        assert "image" in tool_sets
        assert "search" in tool_sets

    def test_get_protected_tool_sets(self):
        """Test that get_protected_tool_sets returns expected mapping."""
        protected_sets = get_protected_tool_sets()

        assert isinstance(protected_sets, dict)

        # Check specific protected tool sets
        assert "homeassistant" in protected_sets
        assert "kepler" in protected_sets
        assert protected_sets["homeassistant"] == "tool-homeassistant"
        assert protected_sets["kepler"] == "tool-kepler"

        # Check that all values follow role naming convention
        for _tool_set, role in protected_sets.items():
            assert isinstance(role, str)
            assert role.startswith("tool-")

    def test_validate_tool_set_keys_valid(self):
        """Test validate_tool_set_keys with valid tool sets."""
        # Single valid tool set
        invalid_keys = validate_tool_set_keys("image")
        assert invalid_keys == []

        # Multiple valid tool sets
        invalid_keys = validate_tool_set_keys("image+search+tts")
        assert invalid_keys == []

        # Empty string
        invalid_keys = validate_tool_set_keys("")
        assert invalid_keys == []

        # None
        invalid_keys = validate_tool_set_keys(None)
        assert invalid_keys == []

    def test_validate_tool_set_keys_invalid(self):
        """Test validate_tool_set_keys with invalid tool sets."""
        # Single invalid tool set
        invalid_keys = validate_tool_set_keys("nonexistent")
        assert "nonexistent" in invalid_keys

        # Mix of valid and invalid
        invalid_keys = validate_tool_set_keys("image+nonexistent+search")
        assert "nonexistent" in invalid_keys
        assert "image" not in invalid_keys
        assert "search" not in invalid_keys

        # Multiple invalid
        invalid_keys = validate_tool_set_keys("invalid1+invalid2")
        assert "invalid1" in invalid_keys
        assert "invalid2" in invalid_keys

    def test_validate_tool_set_keys_edge_cases(self):
        """Test validate_tool_set_keys with edge cases."""
        # Extra spaces and plus signs
        invalid_keys = validate_tool_set_keys(" image + search ")
        assert invalid_keys == []

        # Leading/trailing plus signs
        invalid_keys = validate_tool_set_keys("+image+search+")
        assert invalid_keys == []

        # Empty segments
        invalid_keys = validate_tool_set_keys("image++search")
        assert invalid_keys == []

    def test_get_missing_tool_permissions_no_protected(self):
        """Test get_missing_tool_permissions with non-protected tools."""
        user_roles = ["some-role"]

        # Non-protected tools should not require permissions
        missing = get_missing_tool_permissions("image+search+tts", user_roles)
        assert missing == []

    def test_get_missing_tool_permissions_with_roles(self):
        """Test get_missing_tool_permissions when user has required roles."""
        user_roles = ["tool-homeassistant", "tool-kepler", "other-role"]

        # User has all required roles
        missing = get_missing_tool_permissions("homeassistant+kepler+image", user_roles)
        assert missing == []

    def test_get_missing_tool_permissions_missing_roles(self):
        """Test get_missing_tool_permissions when user lacks required roles."""
        user_roles = ["some-other-role"]

        # User lacks required roles
        missing = get_missing_tool_permissions("homeassistant+kepler", user_roles)
        assert "homeassistant" in missing
        assert "kepler" in missing

    def test_get_missing_tool_permissions_partial_roles(self):
        """Test get_missing_tool_permissions with partial role access."""
        user_roles = ["tool-homeassistant"]

        # User has some but not all required roles
        missing = get_missing_tool_permissions("homeassistant+kepler+image", user_roles)
        assert "homeassistant" not in missing  # User has this role
        assert "kepler" in missing  # User lacks this role
        # image should not be in missing (not protected)

    def test_get_missing_tool_permissions_edge_cases(self):
        """Test get_missing_tool_permissions with edge cases."""
        user_roles = []

        # Empty tool set
        missing = get_missing_tool_permissions("", user_roles)
        assert missing == []

        # None tool set
        missing = get_missing_tool_permissions(None, user_roles)
        assert missing == []


class TestValidateToolSetPermissions:
    """Test cases for validate_tool_set_permissions function."""

    def test_validate_tool_set_permissions_valid(self):
        """Test validate_tool_set_permissions with valid permissions."""
        user_roles = ["tool-homeassistant", "tool-kepler"]

        # Should not raise any exception
        validate_tool_set_permissions("homeassistant+kepler+image", user_roles)
        validate_tool_set_permissions("image+search", user_roles)
        validate_tool_set_permissions("", user_roles)
        validate_tool_set_permissions(None, user_roles)

    def test_validate_tool_set_permissions_invalid_keys(self):
        """Test validate_tool_set_permissions with invalid tool set keys."""
        user_roles = ["tool-homeassistant"]

        with pytest.raises(BadRequest) as exc_info:
            validate_tool_set_permissions("invalid_tool+image", user_roles)

        assert "Invalid tool set keys: invalid_tool" in str(exc_info.value)

    def test_validate_tool_set_permissions_missing_permissions(self):
        """Test validate_tool_set_permissions with missing permissions."""
        user_roles = ["some-other-role"]

        with pytest.raises(Forbidden) as exc_info:
            validate_tool_set_permissions("homeassistant+kepler", user_roles)

        error_message = str(exc_info.value)
        assert "Insufficient permissions for tool sets" in error_message
        assert "homeassistant" in error_message
        assert "kepler" in error_message
        assert "tool-homeassistant" in error_message
        assert "tool-kepler" in error_message

    def test_validate_tool_set_permissions_partial_permissions(self):
        """Test validate_tool_set_permissions with partial permissions."""
        user_roles = ["tool-homeassistant"]

        with pytest.raises(Forbidden) as exc_info:
            validate_tool_set_permissions("homeassistant+kepler", user_roles)

        error_message = str(exc_info.value)
        assert "kepler" in error_message
        assert "homeassistant" not in error_message  # User has this permission

    def test_validate_tool_set_permissions_multiple_invalid_keys(self):
        """Test validate_tool_set_permissions with multiple invalid keys."""
        user_roles = ["tool-homeassistant"]

        with pytest.raises(BadRequest) as exc_info:
            validate_tool_set_permissions("invalid1+invalid2+image", user_roles)

        error_message = str(exc_info.value)
        assert "Invalid tool set keys" in error_message
        assert "invalid1" in error_message
        assert "invalid2" in error_message

    def test_validate_tool_set_permissions_precedence(self):
        """Test that invalid keys are caught before permission checks."""
        user_roles = []  # No roles

        # Should raise BadRequest for invalid keys, not Forbidden for permissions
        with pytest.raises(BadRequest):
            validate_tool_set_permissions("invalid_tool+homeassistant", user_roles)

    def test_validate_tool_set_permissions_edge_cases(self):
        """Test validate_tool_set_permissions with edge cases."""
        user_roles = ["tool-homeassistant", "tool-kepler"]

        # Whitespace handling
        validate_tool_set_permissions(" homeassistant + image ", user_roles)

        # Plus sign handling
        validate_tool_set_permissions("+homeassistant+image+", user_roles)

        # Empty segments
        validate_tool_set_permissions("homeassistant++image", user_roles)
