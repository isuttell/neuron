"""Tests for prompt controller."""

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from quart import Quart
from werkzeug.exceptions import Forbidden, NotFound

from neuron_server.api import app as neuron_app
from neuron_server.controllers.auth import TokenPayload
from neuron_server.controllers.prompt_controller import list_prompts

# Constants
TEST_JWT_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"


@pytest.fixture
def app() -> Quart:
    """Return the Quart app for testing."""
    return neuron_app


@pytest.fixture
def mock_token() -> TokenPayload:
    """Mock JWT token payload."""
    return TokenPayload(
        user_id="test_user_id",
        roles=["user"],
        email="test@example.com",
        nickname="test_user",
        picture=None,
        permissions=[],
    )


@pytest.fixture
def mock_decode_token() -> AsyncMock:
    """Mock decode_token function."""
    with patch("neuron_server.controllers.auth.decode_token") as mock:
        mock.return_value = TokenPayload(
            user_id="test_user_id",
            roles=["user"],
            email="test@example.com",
            nickname="test_user",
            picture=None,
            permissions=[],
        )
        yield mock


@pytest.fixture
def test_context() -> dict:
    """Fixture that combines commonly used test objects."""
    personality_id_1 = uuid4()
    personality_id_2 = uuid4()
    personality_id_3 = uuid4()

    # Create proper mock objects with stable IDs for assertions
    prompt_1_id = uuid4()
    prompt_2_id = uuid4()
    prompt_3_id = uuid4()
    prompt_global_id = uuid4()

    return {
        "user_id": "test_user_id",
        "personality_id_1": personality_id_1,
        "personality_id_2": personality_id_2,
        "personality_id_3": personality_id_3,
        "prompt_1_id": prompt_1_id,
        "prompt_2_id": prompt_2_id,
        "prompt_3_id": prompt_3_id,
        "prompt_global_id": prompt_global_id,
        "accessible_personalities": [
            MagicMock(
                id=personality_id_1,
                name="Accessible Personality 1",
                model_dump=lambda: {
                    "id": str(personality_id_1),
                    "name": "Accessible Personality 1",
                },
            ),
            MagicMock(
                id=personality_id_2,
                name="Accessible Personality 2",
                model_dump=lambda: {
                    "id": str(personality_id_2),
                    "name": "Accessible Personality 2",
                },
            ),
        ],
        "prompts": [
            MagicMock(
                id=prompt_1_id,
                name="Prompt 1",
                text="Test prompt 1",
                personality_id=personality_id_1,
                model_dump=lambda: {
                    "id": str(prompt_1_id),
                    "name": "Prompt 1",
                    "text": "Test prompt 1",
                    "personality_id": str(personality_id_1),
                },
            ),
            MagicMock(
                id=prompt_2_id,
                name="Prompt 2",
                text="Test prompt 2",
                personality_id=personality_id_2,
                model_dump=lambda: {
                    "id": str(prompt_2_id),
                    "name": "Prompt 2",
                    "text": "Test prompt 2",
                    "personality_id": str(personality_id_2),
                },
            ),
            MagicMock(
                id=prompt_3_id,
                name="Prompt 3 - Inaccessible",
                text="Test prompt 3",
                personality_id=personality_id_3,
                model_dump=lambda: {
                    "id": str(prompt_3_id),
                    "name": "Prompt 3 - Inaccessible",
                    "text": "Test prompt 3",
                    "personality_id": str(personality_id_3),
                },
            ),
            MagicMock(
                id=prompt_global_id,
                name="Global Prompt",
                text="Global prompt without personality",
                personality_id=None,
                model_dump=lambda: {
                    "id": str(prompt_global_id),
                    "name": "Global Prompt",
                    "text": "Global prompt without personality",
                    "personality_id": None,
                },
            ),
        ],
    }


@pytest.mark.asyncio
class TestPromptController:
    """Test cases for prompt controller endpoints."""

    async def test_list_prompts_filters_by_user_access(
        self,
        app: Quart,
        mock_token: TokenPayload,
        mock_decode_token: AsyncMock,
        test_context: dict,
    ) -> None:
        """Test list_prompts only returns prompts for accessible personalities."""
        with (
            patch.object(
                __import__(
                    "neuron_server.models.personality_model",
                    fromlist=["PersonalityModel"],
                ).PersonalityModel,
                "list_for_user",
                new_callable=AsyncMock,
            ) as mock_personality_list,
            patch.object(
                __import__(
                    "neuron_server.models.prompt_model", fromlist=["PromptModel"]
                ).PromptModel,
                "list",
                new_callable=AsyncMock,
            ) as mock_prompt_list,
        ):
            # Setup mocks
            mock_personality_list.return_value = test_context[
                "accessible_personalities"
            ]
            mock_prompt_list.return_value = test_context["prompts"]

            # Create request context without personality_id parameter
            async with app.test_request_context(
                "/api/prompts/",
                method="GET",
                headers={"Authorization": TEST_JWT_TOKEN},
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                result = await list_prompts()

                # Verify structure
                assert "prompts" in result
                assert "personalities" in result

                # Should only return prompts for accessible personalities + global
                returned_prompts = result["prompts"]
                assert len(returned_prompts) == 3  # 2 accessible + 1 global

                # Verify no inaccessible prompts are returned
                for prompt in returned_prompts:
                    personality_id = prompt.get("personality_id")
                    if personality_id is not None:
                        assert UUID(personality_id) in {
                            test_context["personality_id_1"],
                            test_context["personality_id_2"],
                        }

                # Should only return accessible personalities
                assert len(result["personalities"]) == 2

                # Verify correct method calls
                mock_personality_list.assert_called_once_with(
                    user_id=test_context["user_id"]
                )
                mock_prompt_list.assert_called_once_with(personality_id=None)

    async def test_list_prompts_with_accessible_personality_id(
        self,
        app: Quart,
        mock_token: TokenPayload,
        mock_decode_token: AsyncMock,
        test_context: dict,
    ) -> None:
        """Test list_prompts respects personality_id param for accessible."""
        with (
            patch.object(
                __import__(
                    "neuron_server.models.personality_model",
                    fromlist=["PersonalityModel"],
                ).PersonalityModel,
                "list_for_user",
                new_callable=AsyncMock,
            ) as mock_personality_list,
            patch.object(
                __import__(
                    "neuron_server.models.prompt_model", fromlist=["PromptModel"]
                ).PromptModel,
                "list",
                new_callable=AsyncMock,
            ) as mock_prompt_list,
        ):
            # Setup mocks
            mock_personality_list.return_value = test_context[
                "accessible_personalities"
            ]
            mock_prompt_list.return_value = test_context["prompts"]

            # Create request context with personality_id parameter
            async with app.test_request_context(
                f"/api/prompts/?personality_id={test_context['personality_id_1']}",
                method="GET",
                headers={"Authorization": TEST_JWT_TOKEN},
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                result = await list_prompts()

                # Should filter to only the requested personality
                assert len(result["personalities"]) == 1
                assert result["personalities"][0]["id"] == str(
                    test_context["personality_id_1"]
                )

                # Verify correct method calls with personality_id
                mock_personality_list.assert_called_once_with(
                    user_id=test_context["user_id"]
                )
                mock_prompt_list.assert_called_once_with(
                    personality_id=test_context["personality_id_1"]
                )

    async def test_list_prompts_with_inaccessible_personality_id_returns_403(
        self,
        app: Quart,
        mock_token: TokenPayload,
        mock_decode_token: AsyncMock,
        test_context: dict,
    ) -> None:
        """Test list_prompts returns 403 when requesting inaccessible personality."""
        with patch.object(
            __import__(
                "neuron_server.models.personality_model", fromlist=["PersonalityModel"]
            ).PersonalityModel,
            "list_for_user",
            new_callable=AsyncMock,
        ) as mock_personality_list:
            # Setup mocks
            mock_personality_list.return_value = test_context[
                "accessible_personalities"
            ]

            # Create request context with inaccessible personality_id parameter
            async with app.test_request_context(
                f"/api/prompts/?personality_id={test_context['personality_id_3']}",
                method="GET",
                headers={"Authorization": TEST_JWT_TOKEN},
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly, expect Forbidden exception
                with pytest.raises(Forbidden) as excinfo:
                    await list_prompts()

                # Verify error message
                assert "don't have access" in str(excinfo.value).lower()

                # Verify security check was performed
                mock_personality_list.assert_called_once_with(
                    user_id=test_context["user_id"]
                )

    async def test_list_prompts_with_invalid_personality_id_returns_404(
        self, app: Quart, mock_token: TokenPayload, mock_decode_token: AsyncMock
    ) -> None:
        """Test that list_prompts returns 404 for invalid UUID format."""
        # Create request context with invalid UUID
        async with app.test_request_context(
            "/api/prompts/?personality_id=invalid-uuid",
            method="GET",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly, expect NotFound exception
            with pytest.raises(NotFound) as excinfo:
                await list_prompts()

            # Verify error message
            assert "invalid" in str(excinfo.value).lower()

    async def test_list_prompts_without_personality_id_returns_all_accessible(
        self,
        app: Quart,
        mock_token: TokenPayload,
        mock_decode_token: AsyncMock,
        test_context: dict,
    ) -> None:
        """Test list_prompts without personality_id returns all accessible prompts."""
        with (
            patch.object(
                __import__(
                    "neuron_server.models.personality_model",
                    fromlist=["PersonalityModel"],
                ).PersonalityModel,
                "list_for_user",
                new_callable=AsyncMock,
            ) as mock_personality_list,
            patch.object(
                __import__(
                    "neuron_server.models.prompt_model", fromlist=["PromptModel"]
                ).PromptModel,
                "list",
                new_callable=AsyncMock,
            ) as mock_prompt_list,
        ):
            # Setup mocks
            mock_personality_list.return_value = test_context[
                "accessible_personalities"
            ]
            mock_prompt_list.return_value = test_context["prompts"]

            # Create request context without personality_id parameter
            async with app.test_request_context(
                "/api/prompts/",
                method="GET",
                headers={"Authorization": TEST_JWT_TOKEN},
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                result = await list_prompts()

                # Should return all accessible personalities
                assert len(result["personalities"]) == 2

                # Should return prompts for accessible personalities + global prompts
                # but NOT prompts for inaccessible personalities
                returned_prompts = result["prompts"]
                inaccessible_prompts = [
                    p
                    for p in returned_prompts
                    if p.get("personality_id") == str(test_context["personality_id_3"])
                ]
                assert len(inaccessible_prompts) == 0

                # Verify method calls
                mock_personality_list.assert_called_once_with(
                    user_id=test_context["user_id"]
                )
                mock_prompt_list.assert_called_once_with(personality_id=None)

    async def test_list_prompts_requires_authentication(self, app: Quart) -> None:
        """Test that list_prompts requires authentication."""
        async with app.test_client() as client:
            response = await client.get("/api/prompts/")

        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN]

    async def test_security_no_data_leakage(
        self,
        app: Quart,
        mock_token: TokenPayload,
        mock_decode_token: AsyncMock,
        test_context: dict,
    ) -> None:
        """Test that the security fix prevents data leakage."""
        # Setup mocks - user only has access to personality_1
        limited_access_personalities = [test_context["accessible_personalities"][0]]

        with (
            patch.object(
                __import__(
                    "neuron_server.models.personality_model",
                    fromlist=["PersonalityModel"],
                ).PersonalityModel,
                "list_for_user",
                new_callable=AsyncMock,
            ) as mock_personality_list,
            patch.object(
                __import__(
                    "neuron_server.models.prompt_model", fromlist=["PromptModel"]
                ).PromptModel,
                "list",
                new_callable=AsyncMock,
            ) as mock_prompt_list,
        ):
            # Setup mocks
            mock_personality_list.return_value = limited_access_personalities
            mock_prompt_list.return_value = test_context["prompts"]

            # Create request context without personality_id parameter
            async with app.test_request_context(
                "/api/prompts/",
                method="GET",
                headers={"Authorization": TEST_JWT_TOKEN},
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                result = await list_prompts()

                # CRITICAL: Should only return 1 personality (user has access to)
                assert len(result["personalities"]) == 1
                assert result["personalities"][0]["id"] == str(
                    test_context["personality_id_1"]
                )

                # Should not contain personalities 2 or 3
                personality_ids = [p["id"] for p in result["personalities"]]
                assert str(test_context["personality_id_2"]) not in personality_ids
                assert str(test_context["personality_id_3"]) not in personality_ids

                # Should only return prompts for accessible personality + global prompts
                returned_prompts = result["prompts"]
                for prompt in returned_prompts:
                    personality_id = prompt.get("personality_id")
                    if personality_id is not None:
                        assert personality_id == str(test_context["personality_id_1"])
