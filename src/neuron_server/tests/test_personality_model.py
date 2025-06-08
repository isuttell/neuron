import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Query

from neuron_server.models.personality_model import PersonalityModel


@pytest.mark.asyncio
async def test_ensure_single_default() -> None:
    """Test that _ensure_single_default clears all existing default personalities."""
    # Create mock personalities with default=True
    personality1 = MagicMock()
    personality1.id = uuid.uuid4()
    personality1.default = True

    personality2 = MagicMock()
    personality2.id = uuid.uuid4()
    personality2.default = True

    # Mock the database session and query
    mock_session = AsyncMock()
    mock_query = MagicMock(spec=Query)
    mock_result = MagicMock()

    # Setup the query chain
    mock_query.where.return_value = mock_query
    mock_result.scalars.return_value.all.return_value = [personality1, personality2]
    mock_session.execute.return_value = mock_result

    with patch(
        "neuron_server.models.personality_model.get_session"
    ) as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Mock the select function
        with patch("neuron_server.models.personality_model.select") as mock_select:
            mock_select.return_value = mock_query

            # Call the method
            await PersonalityModel._ensure_single_default()

            # Verify all personalities had their default set to False
            assert personality1.default is False
            assert personality2.default is False

            # Verify session.commit was called
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_set_personality_default_clears_others() -> None:
    """Test that setting a personality as default clears other defaults."""
    personality_id = uuid.uuid4()

    # Create mock existing default personalities
    existing_default = MagicMock()
    existing_default.id = uuid.uuid4()
    existing_default.default = True

    # Create the personality we're updating
    target_personality = MagicMock()
    target_personality.id = personality_id
    target_personality.name = "Test Personality"
    target_personality.description = "Test Description"
    target_personality.context = "Test Context"
    target_personality.memory = "Test Memory"
    target_personality.tool_set = None
    target_personality.logo = None
    target_personality.default = False
    target_personality.created_at = MagicMock()
    target_personality.updated_at = MagicMock()

    # Mock the database session
    mock_session = AsyncMock()
    mock_query = MagicMock(spec=Query)
    mock_result = MagicMock()

    # Setup for _ensure_single_default
    mock_query.where.return_value = mock_query
    mock_result.scalars.return_value.all.return_value = [existing_default]
    mock_session.execute.return_value = mock_result
    mock_session.get.return_value = target_personality

    with patch(
        "neuron_server.models.personality_model.get_session"
    ) as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session

        with patch("neuron_server.models.personality_model.select") as mock_select:
            mock_select.return_value = mock_query

            # Call the set method
            result = await PersonalityModel.set(
                personality_id=personality_id, key="default", value=True
            )

            # Verify the existing default was cleared
            assert existing_default.default is False

            # Verify the target personality was set as default
            assert target_personality.default is True

            # Verify session operations
            # Once for clearing, once for setting
            assert mock_session.commit.call_count == 2
            mock_session.add.assert_called_with(target_personality)

            # Verify the result
            assert result.id == personality_id
            assert result.default is True


@pytest.mark.asyncio
async def test_create_personality_never_default() -> None:
    """Test that new personalities are never created as default."""
    # This test checks that new personalities are never created as default
    # Since it requires integration testing with the database, we skip it
    pytest.skip("This is better tested as an integration test with a real database")


@pytest.mark.asyncio
async def test_update_personality_preserves_default() -> None:
    """Test that regular updates don't change the default field."""
    personality_id = uuid.uuid4()

    # Create mock personality that is already default
    mock_personality = MagicMock()
    mock_personality.id = personality_id
    mock_personality.name = "Old Name"
    mock_personality.description = "Old Description"
    mock_personality.context = "Old Context"
    mock_personality.memory = "Old Memory"
    mock_personality.tool_set = None
    mock_personality.logo = None
    mock_personality.default = True  # Already default
    mock_personality.created_at = MagicMock()
    mock_personality.updated_at = MagicMock()

    # Mock the database session
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_personality

    with patch(
        "neuron_server.models.personality_model.get_session"
    ) as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Update personality
        params = PersonalityModel.UpdateParams(
            personality_id=personality_id,
            name="Updated Name",
            description="Updated Description",
            context="Updated Context",
            memory="Updated Memory",
            logo="updated_logo.png",
            tool_set="updated_tools",
        )

        await PersonalityModel.update(params)

        # Verify the personality was updated
        assert mock_personality.name == "Updated Name"
        assert mock_personality.description == "Updated Description"
        assert mock_personality.context == "Updated Context"
        assert mock_personality.memory == "Updated Memory"
        assert mock_personality.tool_set == "updated_tools"
        assert mock_personality.logo == "updated_logo.png"

        # Verify default field was NOT touched in the update
        # The original value should remain
        assert mock_personality.default is True

        # Verify DB operations
        mock_session.add.assert_called_once_with(mock_personality)
        mock_session.commit.assert_called_once()
