from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from neuron_server.database import ProviderModel
from neuron_server.models.provider_model import ProviderModelModel


@pytest.mark.asyncio
async def test_provider_model_default_field():
    """Test that the default field is properly handled in provider model"""
    provider_id = uuid4()

    # Create a provider with default=True
    provider = ProviderModelModel(
        id=provider_id,
        provider="openai",
        model_id="gpt-4",
        enabled=False,
        default=True,
        caching_enabled=False,
    )

    # Verify the default field is set
    assert provider.default is True

    # Create another provider with default=False (the default value)
    provider2 = ProviderModelModel(
        id=uuid4(),
        provider="anthropic",
        model_id="claude-3",
        enabled=False,
        caching_enabled=False,
    )

    # Verify the default field defaults to False
    assert provider2.default is False


@pytest.mark.asyncio
async def test_provider_model_save_with_default():
    """Test that the default field is saved correctly to the database"""
    provider_id = uuid4()

    # Create mock database model
    mock_db_model = MagicMock(spec=ProviderModel)
    mock_db_model.id = provider_id
    mock_db_model.provider = "openai"
    mock_db_model.model_id = "gpt-4"
    mock_db_model.enabled = False
    mock_db_model.default = False
    mock_db_model.caching_enabled = False

    # Create mock session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    mock_session.get = AsyncMock(return_value=mock_db_model)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock get_session to return our mock session
    with patch("neuron_server.models.provider_model.get_session") as mock_get_session:
        mock_get_session.return_value = mock_session

        # Create provider model
        provider = ProviderModelModel(
            id=provider_id,
            provider="openai",
            model_id="gpt-4",
            enabled=False,
            default=True,
            caching_enabled=False,
        )

        # Save it
        await provider.save()

        # Verify the default field was set on the database model
        assert mock_db_model.default is True
        assert mock_session.commit.called


@pytest.mark.asyncio
async def test_get_default_provider_when_no_active():
    """Test finding default provider when no active provider exists"""
    provider_id = uuid4()

    # Create mock providers - one default, one not
    mock_provider1 = MagicMock(spec=ProviderModel)
    mock_provider1.id = provider_id
    mock_provider1.provider = "openai"
    mock_provider1.model_id = "gpt-4"
    mock_provider1.enabled = False
    mock_provider1.default = True
    mock_provider1.caching_enabled = False
    mock_provider1.__dict__ = {
        "id": provider_id,
        "provider": "openai",
        "model_id": "gpt-4",
        "enabled": False,
        "default": True,
        "caching_enabled": False,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    mock_provider2 = MagicMock(spec=ProviderModel)
    mock_provider2.id = uuid4()
    mock_provider2.provider = "anthropic"
    mock_provider2.model_id = "claude-3"
    mock_provider2.enabled = False
    mock_provider2.default = False
    mock_provider2.caching_enabled = False
    mock_provider2.__dict__ = {
        "id": mock_provider2.id,
        "provider": "anthropic",
        "model_id": "claude-3",
        "enabled": False,
        "default": False,
        "caching_enabled": False,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    # Mock query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_provider1, mock_provider2]

    # Mock the session - use the mock_session from conftest
    with patch("neuron_server.models.provider_model.get_session") as mock_get_session:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_get_session.return_value = mock_session

        # List all providers
        providers = await ProviderModelModel.list()

        # Find the default provider
        default_providers = [p for p in providers if p.default]
        assert len(default_providers) == 1
        assert default_providers[0].id == provider_id
        assert default_providers[0].default is True


@pytest.mark.asyncio
async def test_get_provider_returns_default_field():
    """Test that get() method returns provider with default field"""
    provider_id = uuid4()

    # Create mock database model
    mock_db_model = MagicMock(spec=ProviderModel)
    mock_db_model.__dict__ = {
        "id": provider_id,
        "provider": "openai",
        "model_id": "gpt-4",
        "enabled": True,
        "default": True,
        "caching_enabled": False,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    # Mock the session directly
    with patch("neuron_server.models.provider_model.get_session") as mock_get_session:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.get = AsyncMock(return_value=mock_db_model)
        mock_get_session.return_value = mock_session

        # Get provider
        provider = await ProviderModelModel.get(provider_id)

        # Verify the default field is included
        assert provider is not None
        assert provider.default is True
        assert provider.id == provider_id
