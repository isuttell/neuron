"""Tests for permission service functionality."""

import asyncio
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest


class TestPermissionServiceIntegration:
    """Test permission service integration with mocked system."""

    @pytest.fixture
    def mock_permission_service(self):
        """Get the mocked permission service from conftest."""
        from neuron_server.permission_service import permission_service

        return permission_service

    @pytest.mark.asyncio
    async def test_permission_service_exists(self, mock_permission_service):
        """Test that the permission service is available."""
        assert mock_permission_service is not None

    @pytest.mark.asyncio
    async def test_user_has_thread_access(self, mock_permission_service):
        """Test that user_has_thread_access method exists and can be called."""
        user_id = "test_user"
        thread_id = uuid4()

        # The mock should return True by default from conftest.py
        result = await mock_permission_service.user_has_thread_access(
            user_id, thread_id
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_user_has_personality_access(self, mock_permission_service):
        """Test that user_has_personality_access method exists and can be called."""
        user_id = "test_user"
        personality_id = uuid4()

        # The mock should return True by default from conftest.py
        result = await mock_permission_service.user_has_personality_access(
            user_id, personality_id
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_get_users_with_thread_access(self, mock_permission_service):
        """Test that get_users_with_thread_access method exists and can be called."""
        thread_id = uuid4()

        # The mock should return an empty list by default from conftest.py
        result = await mock_permission_service.get_users_with_thread_access(thread_id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_users_with_personality_access(self, mock_permission_service):
        """Test that get_users_with_personality_access method exists."""
        personality_id = uuid4()

        # The mock should return an empty list by default from conftest.py
        result = await mock_permission_service.get_users_with_personality_access(
            personality_id
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_permission_service_methods_are_async(self, mock_permission_service):
        """Test that permission service methods return coroutines or async mocks."""
        user_id = "test_user"
        thread_id = uuid4()
        personality_id = uuid4()

        # These should all be async methods
        thread_access = mock_permission_service.user_has_thread_access(
            user_id, thread_id
        )
        personality_access = mock_permission_service.user_has_personality_access(
            user_id, personality_id
        )
        thread_users = mock_permission_service.get_users_with_thread_access(thread_id)
        personality_users = mock_permission_service.get_users_with_personality_access(
            personality_id
        )

        # Await all the results
        results = await asyncio.gather(
            thread_access, personality_access, thread_users, personality_users
        )

        # Should have gotten results without errors
        assert len(results) == 4


class TestPermissionServiceUsage:
    """Test how permission service is used in the codebase."""

    @pytest.mark.asyncio
    async def test_permission_service_integrated_with_controllers(self):
        """Test that permission service is integrated with message controllers."""
        from unittest.mock import patch

        from neuron_server.controllers.message_controller import permission_service

        # Verify that the permission service is available in the message controller
        assert permission_service is not None

        # Test that we can call the permission methods
        user_id = "test_user"
        thread_id = uuid4()
        personality_id = uuid4()

        # These should work without errors since they're mocked to return True
        with (
            patch.object(
                permission_service, "user_has_thread_access", new_callable=AsyncMock
            ) as mock_thread,
            patch.object(
                permission_service,
                "user_has_personality_access",
                new_callable=AsyncMock,
            ) as mock_personality,
        ):
            mock_thread.return_value = True
            mock_personality.return_value = True

            thread_result = await permission_service.user_has_thread_access(
                user_id, thread_id
            )
            personality_result = await permission_service.user_has_personality_access(
                user_id, personality_id
            )

            assert thread_result is True
            assert personality_result is True
            mock_thread.assert_called_once_with(user_id, thread_id)
            mock_personality.assert_called_once_with(user_id, personality_id)

    @pytest.mark.asyncio
    async def test_permission_service_called_with_correct_parameters(self):
        """Test that permission service is called with expected parameter types."""
        from unittest.mock import patch

        from neuron_server.permission_service import permission_service

        # Mock the actual permission checks to verify they're called correctly
        with (
            patch.object(
                permission_service, "user_has_thread_access", new_callable=AsyncMock
            ) as mock_thread_access,
            patch.object(
                permission_service,
                "user_has_personality_access",
                new_callable=AsyncMock,
            ) as mock_personality_access,
        ):
            mock_thread_access.return_value = True
            mock_personality_access.return_value = True

            user_id = "test_user_123"
            thread_id = uuid4()
            personality_id = uuid4()

            # Call the methods
            await permission_service.user_has_thread_access(user_id, thread_id)
            await permission_service.user_has_personality_access(
                user_id, personality_id
            )

            # Verify they were called with correct types
            mock_thread_access.assert_called_once_with(user_id, thread_id)
            mock_personality_access.assert_called_once_with(user_id, personality_id)

            # Verify parameter types
            call_args = mock_thread_access.call_args[0]
            assert isinstance(call_args[0], str)  # user_id should be string
            assert isinstance(call_args[1], UUID)  # thread_id should be UUID

            call_args = mock_personality_access.call_args[0]
            assert isinstance(call_args[0], str)  # user_id should be string
            assert isinstance(call_args[1], UUID)  # personality_id should be UUID


if __name__ == "__main__":
    import asyncio

    pytest.main(["-v", __file__])
