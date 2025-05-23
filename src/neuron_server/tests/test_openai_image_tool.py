"""Unit tests for OpenAI Image Generation Tool."""

import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
from pydantic import ValidationError

from neuron_server.tools.openai_image_tool import (
    OpenAIImageArgs,
    OpenAIImageGenerationTool,
)


class TestOpenAIImageArgs:
    """Tests for the OpenAIImageArgs model."""

    def test_valid_args(self) -> None:
        """Test valid arguments."""
        args = OpenAIImageArgs(
            name="test_image",
            prompt="A cat sitting on a chair",
        )
        assert args.name == "test_image"
        assert args.prompt == "A cat sitting on a chair"
        assert args.size == "auto"
        assert args.quality == "auto"
        assert args.background == "auto"
        assert args.output_format == "png"
        assert args.n == 1
        assert args.image_id is None
        assert args.image_url is None

    def test_valid_args_with_all_parameters(self) -> None:
        """Test valid arguments with all parameters specified."""
        args = OpenAIImageArgs(
            name="detailed_image",
            prompt="A detailed landscape",
            size="1024x1536",
            quality="high",
            background="transparent",
            output_format="webp",
            n=2,
            image_id="img_123",
        )
        assert args.name == "detailed_image"
        assert args.prompt == "A detailed landscape"
        assert args.size == "1024x1536"
        assert args.quality == "high"
        assert args.background == "transparent"
        assert args.output_format == "webp"
        expected_n = 2
        assert args.n == expected_n
        assert args.image_id == "img_123"
        assert args.image_url is None

    def test_valid_args_with_image_url(self) -> None:
        """Test valid arguments with image_url parameter."""
        args = OpenAIImageArgs(
            name="test_image",
            prompt="A cat sitting on a chair",
            image_url="https://example.com/image.jpg",
        )
        assert args.name == "test_image"
        assert args.prompt == "A cat sitting on a chair"
        assert args.image_url == "https://example.com/image.jpg"

    def test_invalid_size(self) -> None:
        """Test invalid size parameter."""
        with pytest.raises(ValidationError):
            OpenAIImageArgs(
                name="test",
                prompt="test",
                size="invalid_size",  # type: ignore
            )

    def test_invalid_quality(self) -> None:
        """Test invalid quality parameter."""
        with pytest.raises(ValidationError):
            OpenAIImageArgs(
                name="test",
                prompt="test",
                quality="invalid_quality",  # type: ignore
            )

    def test_invalid_background(self) -> None:
        """Test invalid background parameter."""
        with pytest.raises(ValidationError):
            OpenAIImageArgs(
                name="test",
                prompt="test",
                background="invalid_background",  # type: ignore
            )

    def test_invalid_output_format(self) -> None:
        """Test invalid output format parameter."""
        with pytest.raises(ValidationError):
            OpenAIImageArgs(
                name="test",
                prompt="test",
                output_format="invalid_format",  # type: ignore
            )


class TestOpenAIImageGenerationTool:
    """Tests for the OpenAIImageGenerationTool."""

    @pytest.fixture
    def tool(self) -> OpenAIImageGenerationTool:
        """Create a tool instance for testing."""
        return OpenAIImageGenerationTool()

    @pytest.fixture
    def mock_config(self) -> dict:
        """Create a mock config for testing."""
        return {
            "configurable": {
                "thread_id": "test_thread_123",
                "user_id": "test_user_456",
            }
        }

    @pytest.fixture
    def sample_image_base64(self) -> str:
        """Create a sample base64 encoded image for testing."""
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()

    def test_tool_properties(self, tool: OpenAIImageGenerationTool) -> None:
        """Test tool basic properties."""
        assert tool.name == "openai_image_generation"
        assert "GPT-Image-1" in tool.description
        assert "multi-turn" in tool.description
        assert tool.args_schema == OpenAIImageArgs

    @pytest.mark.asyncio
    async def test_successful_image_generation(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
        sample_image_base64: str,
    ) -> None:
        """Test successful image generation without multi-turn."""
        # Mock the OpenAI client and response
        mock_call = MagicMock()
        mock_call.id = "img_call_123"
        mock_call.type = "image_generation_call"
        mock_call.status = "completed"
        mock_call.result = sample_image_base64
        mock_call.revised_prompt = "A beautiful cat sitting gracefully"

        mock_response = MagicMock()
        mock_response.output = [mock_call]

        mock_client = AsyncMock()
        mock_client.responses.create.return_value = mock_response

        mock_media_item = MagicMock()
        mock_media_item.id = "media_123"

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch(
                "neuron_server.tools.openai_image_tool.MediaItemModel"
            ) as mock_media_model,
            patch("neuron_server.tools.openai_image_tool.create_thumbnails"),
            patch(
                "neuron_server.tools.openai_image_tool.safe_filename",
                return_value="test_image.png"
            ),
            patch("neuron_server.config.config") as mock_config_module,
            patch(
                "neuron_server.tools.openai_image_tool.Image.open"
            ) as mock_image_open,
        ):

            # Mock Image.open and save
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            mock_openai.return_value = mock_client
            mock_media_model.create = AsyncMock(return_value=mock_media_item)
            mock_config_module.openai_api_key = "test_key"
            mock_config_module.static_folder = "/tmp"
            mock_config_module.static_content_url = "http://test.com/static"

            result = await tool._arun(
                name="test_image",
                prompt="A cat sitting on a chair",
                config=mock_config,
            )

            # Verify OpenAI client was called correctly
            mock_client.responses.create.assert_called_once()
            call_args = mock_client.responses.create.call_args
            assert call_args[1]["model"] == "gpt-4.1-mini"
            assert call_args[1]["input"] == "A cat sitting on a chair"
            assert call_args[1]["tools"][0]["type"] == "image_generation"

            # Verify media item was created
            mock_media_model.create.assert_called_once()
            # Just verify it was called, detailed validation in integration tests
            assert mock_media_model.create.called

            # Verify result format
            assert "<images>" in result
            assert "<image id=\"media_123\">" in result
            assert "<image_id>img_call_123</image_id>" in result
            assert "![A beautiful cat sitting gracefully]" in result

    @pytest.mark.asyncio
    async def test_successful_image_generation_with_multi_turn(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
        sample_image_base64: str,
    ) -> None:
        """Test successful image generation with multi-turn editing."""
        # Mock the OpenAI client and response
        mock_call = MagicMock()
        mock_call.id = "img_call_456"
        mock_call.type = "image_generation_call"
        mock_call.status = "completed"
        mock_call.result = sample_image_base64
        mock_call.revised_prompt = "A realistic cat sitting gracefully"

        mock_response = MagicMock()
        mock_response.output = [mock_call]

        mock_client = AsyncMock()
        mock_client.responses.create.return_value = mock_response

        mock_media_item = MagicMock()
        mock_media_item.id = "media_456"

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch(
                "neuron_server.tools.openai_image_tool.MediaItemModel"
            ) as mock_media_model,
            patch("neuron_server.tools.openai_image_tool.create_thumbnails"),
            patch(
                "neuron_server.tools.openai_image_tool.safe_filename",
                return_value="test_edit.png"
            ),
            patch("neuron_server.config.config") as mock_config_module,
            patch(
                "neuron_server.tools.openai_image_tool.Image.open"
            ) as mock_image_open,
        ):

            # Mock Image.open and save
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            mock_openai.return_value = mock_client
            mock_media_model.create = AsyncMock(return_value=mock_media_item)
            mock_config_module.openai_api_key = "test_key"
            mock_config_module.static_folder = "/tmp"
            mock_config_module.static_content_url = "http://test.com/static"

            result = await tool._arun(
                name="realistic_cat",
                prompt="Make it look more realistic",
                config=mock_config,
                image_id="img_call_123",  # Previous image call ID
            )

            # Verify OpenAI client was called with multi-turn input
            mock_client.responses.create.assert_called_once()
            call_args = mock_client.responses.create.call_args
            assert call_args[1]["model"] == "gpt-4.1-mini"

            # Check multi-turn input structure
            input_data = call_args[1]["input"]
            assert isinstance(input_data, list)
            expected_input_length = 2
            assert len(input_data) == expected_input_length
            assert input_data[0]["role"] == "user"
            assert input_data[0]["content"][0]["text"] == "Make it look more realistic"
            assert input_data[1]["type"] == "image_generation_call"
            assert input_data[1]["id"] == "img_call_123"

            # Verify result contains multi-turn reference
            assert "<image_id>img_call_456</image_id>" in result

    @pytest.mark.asyncio
    async def test_custom_parameters(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
        sample_image_base64: str,
    ) -> None:
        """Test image generation with custom parameters."""
        mock_call = MagicMock()
        mock_call.id = "img_call_789"
        mock_call.type = "image_generation_call"
        mock_call.status = "completed"
        mock_call.result = sample_image_base64

        mock_response = MagicMock()
        mock_response.output = [mock_call]

        mock_client = AsyncMock()
        mock_client.responses.create.return_value = mock_response

        mock_media_item = MagicMock()
        mock_media_item.id = "media_789"

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch(
                "neuron_server.tools.openai_image_tool.MediaItemModel"
            ) as mock_media_model,
            patch("neuron_server.tools.openai_image_tool.create_thumbnails"),
            patch(
                "neuron_server.tools.openai_image_tool.safe_filename",
                return_value="test_custom.jpg"
            ),
            patch("neuron_server.config.config") as mock_config_module,
            patch(
                "neuron_server.tools.openai_image_tool.Image.open"
            ) as mock_image_open,
        ):

            # Mock Image.open and save
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            mock_openai.return_value = mock_client
            mock_media_model.create = AsyncMock(return_value=mock_media_item)
            mock_config_module.openai_api_key = "test_key"
            mock_config_module.static_folder = "/tmp"
            mock_config_module.static_content_url = "http://test.com/static"

            await tool._arun(
                name="custom_image",
                prompt="A landscape with mountains",
                config=mock_config,
                size="1536x1024",
                quality="high",
                background="transparent",
                output_format="jpeg",
            )

            # Verify custom parameters were passed to the tool
            call_args = mock_client.responses.create.call_args
            image_tool = call_args[1]["tools"][0]
            assert image_tool["size"] == "1536x1024"
            assert image_tool["quality"] == "high"
            assert image_tool["background"] == "transparent"
            assert image_tool["output_format"] == "jpeg"

    @pytest.mark.asyncio
    async def test_failed_generation_no_calls(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
    ) -> None:
        """Test handling when no image generation calls are returned."""
        mock_response = MagicMock()
        mock_response.output = []  # No image generation calls

        mock_client = AsyncMock()
        mock_client.responses.create.return_value = mock_response

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch("neuron_server.config.config") as mock_config_module,
        ):
            mock_openai.return_value = mock_client
            mock_config_module.openai_api_key = "test_key"

            result = await tool._arun(
                name="test_image",
                prompt="A cat",
                config=mock_config,
            )

            assert "Error: No image generation calls found in response" in result

    @pytest.mark.asyncio
    async def test_failed_generation_incomplete_status(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
    ) -> None:
        """Test handling when image generation call has incomplete status."""
        mock_call = MagicMock()
        mock_call.id = "img_call_failed"
        mock_call.type = "image_generation_call"
        mock_call.status = "failed"

        mock_response = MagicMock()
        mock_response.output = [mock_call]

        mock_client = AsyncMock()
        mock_client.responses.create.return_value = mock_response

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch("neuron_server.config.config") as mock_config_module,
        ):
            mock_openai.return_value = mock_client
            mock_config_module.openai_api_key = "test_key"

            result = await tool._arun(
                name="test_image",
                prompt="A cat",
                config=mock_config,
            )

            assert "Error: No images were successfully generated" in result

    @pytest.mark.asyncio
    async def test_openai_api_exception(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
    ) -> None:
        """Test handling of OpenAI API exceptions."""
        mock_client = AsyncMock()
        mock_client.responses.create.side_effect = Exception("API Error")

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch("neuron_server.config.config") as mock_config_module,
        ):
            mock_openai.return_value = mock_client
            mock_config_module.openai_api_key = "test_key"

            result = await tool._arun(
                name="test_image",
                prompt="A cat",
                config=mock_config,
            )

            assert "Error generating image: API Error" in result

    @pytest.mark.asyncio
    async def test_webp_output_format(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
        sample_image_base64: str,
    ) -> None:
        """Test WebP output format handling."""
        mock_call = MagicMock()
        mock_call.id = "img_call_webp"
        mock_call.type = "image_generation_call"
        mock_call.status = "completed"
        mock_call.result = sample_image_base64

        mock_response = MagicMock()
        mock_response.output = [mock_call]

        mock_client = AsyncMock()
        mock_client.responses.create.return_value = mock_response

        mock_media_item = MagicMock()
        mock_media_item.id = "media_webp"

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch(
                "neuron_server.tools.openai_image_tool.MediaItemModel"
            ) as mock_media_model,
            patch("neuron_server.tools.openai_image_tool.create_thumbnails"),
            patch(
                "neuron_server.tools.openai_image_tool.safe_filename",
                return_value="test.webp"
            ),
            patch("neuron_server.config.config") as mock_config_module,
            patch(
                "neuron_server.tools.openai_image_tool.Image.open"
            ) as mock_image_open,
        ):

            # Mock Image.open and save
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            mock_openai.return_value = mock_client
            mock_media_model.create = AsyncMock(return_value=mock_media_item)
            mock_config_module.openai_api_key = "test_key"
            mock_config_module.static_folder = "/tmp"
            mock_config_module.static_content_url = "http://test.com/static"

            result = await tool._arun(
                name="webp_image",
                prompt="A test image",
                config=mock_config,
                output_format="webp",
            )

            # Verify WebP format was requested
            call_args = mock_client.responses.create.call_args
            assert call_args[1]["tools"][0]["output_format"] == "webp"

            # Verify successful result
            assert "<images>" in result
            assert "media_webp" in result

    def test_sync_run_method(self, tool: OpenAIImageGenerationTool) -> None:
        """Test that the sync _run method calls the async _arun method."""
        with patch.object(tool, '_arun', return_value="test_result") as mock_arun:
            result = tool._run(
                name="test",
                prompt="test prompt",
                config={"configurable": {}},
            )

            mock_arun.assert_called_once()
            assert result == "test_result"


    @pytest.mark.asyncio
    async def test_image_url_generation(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
        sample_image_base64: str,
    ) -> None:
        """Test image generation using image_url parameter."""
        # Mock image download
        mock_downloaded_base64 = "test_downloaded_image_base64"

        mock_call = MagicMock()
        mock_call.id = "img_call_from_url"
        mock_call.type = "image_generation_call"
        mock_call.status = "completed"
        mock_call.result = sample_image_base64

        mock_response = MagicMock()
        mock_response.output = [mock_call]

        mock_client = AsyncMock()
        mock_client.responses.create.return_value = mock_response

        mock_media_item = MagicMock()
        mock_media_item.id = "media_from_url"

        with (
            patch(
                "neuron_server.tools.openai_image_tool.AsyncOpenAI"
            ) as mock_openai,
            patch(
                "neuron_server.tools.openai_image_tool.MediaItemModel"
            ) as mock_media_model,
            patch("neuron_server.tools.openai_image_tool.create_thumbnails"),
            patch(
                "neuron_server.tools.openai_image_tool.safe_filename",
                return_value="test_from_url.png"
            ),
            patch("neuron_server.config.config") as mock_config_module,
            patch(
                "neuron_server.tools.openai_image_tool.Image.open"
            ) as mock_image_open,
            patch.object(
                tool, '_download_and_encode_image',
                return_value=mock_downloaded_base64
            ) as mock_download,
        ):

            # Mock Image.open and save
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            mock_openai.return_value = mock_client
            mock_media_model.create = AsyncMock(return_value=mock_media_item)
            mock_config_module.openai_api_key = "test_key"
            mock_config_module.static_folder = "/tmp"
            mock_config_module.static_content_url = "http://test.com/static"

            result = await tool._arun(
                name="image_from_url",
                prompt="Modify this image to be darker",
                config=mock_config,
                image_url="https://example.com/source.jpg",
            )

            # Verify image was downloaded
            mock_download.assert_called_once_with("https://example.com/source.jpg")

            # Verify the API call included image input
            call_args = mock_client.responses.create.call_args
            input_data = call_args[1]["input"]
            assert isinstance(input_data, list)
            expected_input_length = 1
            assert len(input_data) == expected_input_length
            assert input_data[0]["role"] == "user"

            content = input_data[0]["content"]
            expected_content_length = 2
            assert len(content) == expected_content_length
            assert content[0]["type"] == "input_text"
            assert content[0]["text"] == "Modify this image to be darker"
            assert content[1]["type"] == "input_image"
            expected_image_url = (
                f"data:image/jpeg;base64,{mock_downloaded_base64}"
            )
            assert content[1]["image_url"] == expected_image_url

            # Verify successful result
            assert "<images>" in result
            assert "media_from_url" in result

    @pytest.mark.asyncio
    async def test_image_url_download_error(
        self,
        tool: OpenAIImageGenerationTool,
        mock_config: dict,
    ) -> None:
        """Test handling of image download errors."""
        with patch.object(
            tool, '_download_and_encode_image',
            side_effect=Exception("Download failed")
        ):
            result = await tool._arun(
                name="error_image",
                prompt="Test prompt",
                config=mock_config,
                image_url="https://example.com/nonexistent.jpg",
            )

            assert "Error generating image: Download failed" in result
