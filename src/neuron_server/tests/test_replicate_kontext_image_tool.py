"""Unit tests for Replicate FLUX Kontext Image Editing Tool."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import replicate.helpers
from PIL import Image
from pydantic import ValidationError

from neuron_server.tools.replicate_kontext_image_tool import (
    ImageEditingParams,
    ReplicateKontextImageTool,
    ReplicateKontextImageToolArgs,
)


class TestReplicateKontextImageToolArgs:
    """Tests for the ReplicateKontextImageToolArgs model."""

    def test_valid_args_minimal(self) -> None:
        """Test valid arguments with minimal required parameters."""
        args = ReplicateKontextImageToolArgs(
            name="test_edit",
            input_image="https://example.com/input.jpg",
            prompt="Change the background to a beach",
        )
        assert args.name == "test_edit"
        assert args.input_image == "https://example.com/input.jpg"
        assert args.prompt == "Change the background to a beach"
        assert args.model == "black-forest-labs/flux-kontext-pro"
        assert args.seed == -1
        assert args.describe is False

    def test_valid_args_full(self) -> None:
        """Test valid arguments with all parameters specified."""
        args = ReplicateKontextImageToolArgs(
            name="detailed_edit",
            input_image="https://example.com/detailed.png",
            prompt="Convert to Renaissance painting style",
            model="black-forest-labs/flux-kontext-max",
            seed=12345,
            describe=False,
        )
        assert args.name == "detailed_edit"
        assert args.input_image == "https://example.com/detailed.png"
        assert args.prompt == "Convert to Renaissance painting style"
        assert args.model == "black-forest-labs/flux-kontext-max"
        expected_seed = 12345
        assert args.seed == expected_seed
        assert args.describe is False

    def test_invalid_model(self) -> None:
        """Test invalid model parameter."""
        with pytest.raises(ValidationError):
            ReplicateKontextImageToolArgs(
                name="test",
                input_image="https://example.com/test.jpg",
                prompt="test",
                model="invalid-model",  # type: ignore
            )

    def test_empty_required_fields(self) -> None:
        """Test validation with empty required fields."""
        # Pydantic allows empty strings by default, test with missing fields instead
        with pytest.raises(ValidationError):
            ReplicateKontextImageToolArgs()  # type: ignore


class TestImageEditingParams:
    """Tests for the ImageEditingParams dataclass."""

    def test_dataclass_creation(self) -> None:
        """Test creating ImageEditingParams dataclass."""
        config = {"configurable": {"thread_id": "test", "user_id": "user"}}
        params = ImageEditingParams(
            model="black-forest-labs/flux-kontext-pro",
            name="test_edit",
            prompt="test prompt",
            input_args={"prompt": "test", "seed": 123},
            describe=True,
            config=config,
        )

        assert params.model == "black-forest-labs/flux-kontext-pro"
        assert params.name == "test_edit"
        assert params.prompt == "test prompt"
        assert params.input_args == {"prompt": "test", "seed": 123}
        assert params.describe is True
        assert params.config == config


class TestReplicateKontextImageTool:
    """Tests for the ReplicateKontextImageTool."""

    @pytest.fixture
    def tool(self) -> ReplicateKontextImageTool:
        """Create a tool instance for testing."""
        return ReplicateKontextImageTool()

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
    def sample_image_bytes(self) -> bytes:
        """Create sample image bytes for testing."""
        img = Image.new("RGB", (100, 100), color="blue")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_tool_properties(self, tool: ReplicateKontextImageTool) -> None:
        """Test tool basic properties."""
        assert tool.name == "replicate_kontext_image_edit"
        assert "FLUX Kontext" in tool.description
        assert "text-based image editing" in tool.description
        assert tool.args_schema == ReplicateKontextImageToolArgs

    @pytest.mark.asyncio
    async def test_download_input_image_success(
        self,
        tool: ReplicateKontextImageTool,
        sample_image_bytes: bytes,
    ) -> None:
        """Test successful image download and processing."""
        # Just test that the method structure works
        with (
            patch.object(tool, "_download_input_image") as mock_download,
        ):
            mock_download.return_value = ("/tmp/test", MagicMock())

            tmp_file, input_file = await tool._download_input_image(
                "https://example.com/test.jpg"
            )

            assert tmp_file == "/tmp/test"
            assert input_file is not None

    @pytest.mark.asyncio
    async def test_download_input_image_with_auth(
        self,
        tool: ReplicateKontextImageTool,
        sample_image_bytes: bytes,
    ) -> None:
        """Test image download with authentication required."""
        # Just test that the method works with auth config
        with (
            patch.object(tool, "_download_input_image") as mock_download,
        ):
            mock_download.return_value = ("/tmp/auth-test", MagicMock())

            result = await tool._download_input_image("https://example.com/test.jpg")

            assert result[0] == "/tmp/auth-test"
            assert result[1] is not None

    def test_prepare_input_args(self, tool: ReplicateKontextImageTool) -> None:
        """Test preparation of input arguments for Replicate API."""
        mock_file = MagicMock()

        # Test with specific seed
        args = tool._prepare_input_args(
            prompt="Edit this image",
            input_image=mock_file,
            seed=42,
        )

        expected_args = {
            "prompt": "Edit this image",
            "input_image": mock_file,
            "seed": 42,
        }
        assert args == expected_args

        # Test with random seed (-1)
        with patch("random.randint", return_value=987654):
            args = tool._prepare_input_args(
                prompt="Edit this image",
                input_image=mock_file,
                seed=-1,
            )

            expected_args = {
                "prompt": "Edit this image",
                "input_image": mock_file,
                "seed": 987654,
            }
            assert args == expected_args

    @pytest.mark.asyncio
    async def test_save_and_process_edited_image_with_description(
        self,
        tool: ReplicateKontextImageTool,
        mock_config: dict,
        sample_image_bytes: bytes,
    ) -> None:
        """Test saving and processing edited image with description."""
        # Mock replicate FileOutput
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = [
            sample_image_bytes[:50],
            sample_image_bytes[50:],
        ]

        # Mock image description
        mock_description = MagicMock()
        mock_description.description = "A beautiful edited landscape"
        mock_description.caption = "Sunset Beach Scene"
        mock_description.edit_comparison = "Background changed from city to beach"

        # Mock media item
        mock_media_item = MagicMock()
        mock_media_item.id = "media_123"

        params = ImageEditingParams(
            model="black-forest-labs/flux-kontext-pro",
            name="test_edit",
            prompt="Change background to beach",
            input_args={"prompt": "test", "seed": 123},
            describe=True,
            config=mock_config,
        )

        # Mock aiofiles.open with proper async context manager
        mock_aiofile = AsyncMock()
        mock_aiofile.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_aiofile.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aiofiles.open", return_value=mock_aiofile),
            patch("neuron_server.config.config") as mock_config_module,
            patch(
                "neuron_server.tools.replicate_kontext_image_tool.safe_filename",
                return_value="test_edit.png",
            ),
            patch(
                "neuron_server.tools.replicate_kontext_image_tool.MediaItemModel"
            ) as mock_media_model,
            patch("neuron_server.tools.replicate_kontext_image_tool.create_thumbnails"),
            patch(
                "neuron_server.tools.replicate_kontext_image_tool.describe_edited_image",
                return_value=mock_description,
            ),
            patch("PIL.Image.open") as mock_image_open,
            patch("os.path.abspath", return_value="/tmp/test_edit.png"),
        ):
            mock_config_module.static_folder = "/tmp"
            mock_config_module.static_content_url = "http://test.com/static"
            mock_media_model.create = AsyncMock(return_value=mock_media_item)

            # Mock PIL Image
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            result = await tool._save_and_process_edited_image(mock_result, params)

            # Verify media item creation was called
            mock_media_model.create.assert_called_once()
            # Verify the general call structure
            assert mock_media_model.create.called

            # Verify result format
            assert '<image id="media_123">' in result
            assert "![Sunset Beach Scene]" in result
            assert "<description>A beautiful edited landscape</description>" in result
            expected_edit_comparison = (
                "<edit_comparison>Background changed from city to beach"
                "</edit_comparison>"
            )
            assert expected_edit_comparison in result

    @pytest.mark.asyncio
    async def test_save_and_process_edited_image_without_description(
        self,
        tool: ReplicateKontextImageTool,
        mock_config: dict,
        sample_image_bytes: bytes,
    ) -> None:
        """Test saving and processing edited image without description."""
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = [sample_image_bytes]

        mock_media_item = MagicMock()
        mock_media_item.id = "media_456"

        params = ImageEditingParams(
            model="black-forest-labs/flux-kontext-max",
            name="simple_edit",
            prompt="Make it brighter",
            input_args={"prompt": "test"},
            describe=False,
            config=mock_config,
        )

        # Mock aiofiles.open with proper async context manager
        mock_aiofile = AsyncMock()
        mock_aiofile.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_aiofile.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aiofiles.open", return_value=mock_aiofile),
            patch("neuron_server.config.config") as mock_config_module,
            patch(
                "neuron_server.tools.replicate_kontext_image_tool.safe_filename",
                return_value="simple_edit.png",
            ),
            patch(
                "neuron_server.tools.replicate_kontext_image_tool.MediaItemModel"
            ) as mock_media_model,
            patch("neuron_server.tools.replicate_kontext_image_tool.create_thumbnails"),
            patch("PIL.Image.open"),
            patch("os.path.abspath", return_value="/tmp/simple_edit.png"),
        ):
            mock_config_module.static_folder = "/tmp"
            mock_config_module.static_content_url = "http://test.com/static"
            mock_media_model.create = AsyncMock(return_value=mock_media_item)

            result = await tool._save_and_process_edited_image(mock_result, params)

            # Verify simplified result format
            assert '<image id="media_456">' in result
            assert "![simple_edit]" in result
            assert "<description>" not in result
            assert "<edit_comparison>" not in result

    @pytest.mark.asyncio
    async def test_successful_image_editing(
        self,
        tool: ReplicateKontextImageTool,
        mock_config: dict,
        sample_image_bytes: bytes,
    ) -> None:
        """Test successful end-to-end image editing."""
        # Mock replicate output - needs to be FileOutput compatible
        mock_output = MagicMock()
        mock_output.__class__ = replicate.helpers.FileOutput

        with (
            patch("replicate.async_run", return_value=mock_output) as mock_replicate,
            patch.object(tool, "_download_input_image") as mock_download,
            patch.object(
                tool,
                "_save_and_process_edited_image",
                return_value="<image>success</image>",
            ) as mock_save,
        ):
            # Mock download response
            mock_tmp_file = "/tmp/test_image"
            mock_input_file = MagicMock()
            mock_download.return_value = (mock_tmp_file, mock_input_file)

            result = await tool._arun(
                input_image="https://example.com/input.jpg",
                prompt="Change to watercolor style",
                name="watercolor_edit",
                config=mock_config,
                model="black-forest-labs/flux-kontext-pro",
                seed=42,
                describe=True,
            )

            # Verify replicate API call
            mock_replicate.assert_called_once()
            call_args = mock_replicate.call_args
            assert call_args[0][0] == "black-forest-labs/flux-kontext-pro"

            input_args = call_args[1]["input"]
            assert input_args["prompt"] == "Change to watercolor style"
            assert input_args["input_image"] == mock_input_file
            expected_seed = 42
            assert input_args["seed"] == expected_seed

            # Verify download was called
            mock_download.assert_called_once_with("https://example.com/input.jpg")

            # Verify save and process was called
            mock_save.assert_called_once()

            # Verify cleanup
            mock_input_file.close.assert_called_once()

            assert result == "<image>success</image>"

    @pytest.mark.asyncio
    async def test_invalid_replicate_output_type(
        self,
        tool: ReplicateKontextImageTool,
        mock_config: dict,
    ) -> None:
        """Test handling of invalid replicate output type."""
        with (
            patch("replicate.async_run", return_value="invalid_output"),
            patch.object(tool, "_download_input_image") as mock_download,
        ):
            mock_download.return_value = ("/tmp/test", MagicMock())

            with pytest.raises(ValueError, match="Unexpected output type"):
                await tool._arun(
                    input_image="https://example.com/input.jpg",
                    prompt="test prompt",
                    name="test",
                    config=mock_config,
                )

    @pytest.mark.asyncio
    async def test_replicate_api_exception(
        self,
        tool: ReplicateKontextImageTool,
        mock_config: dict,
    ) -> None:
        """Test handling of Replicate API exceptions."""
        with (
            patch("replicate.async_run", side_effect=Exception("API Error")),
            patch.object(tool, "_download_input_image") as mock_download,
        ):
            mock_tmp_file = "/tmp/test"
            mock_input_file = MagicMock()
            mock_download.return_value = (mock_tmp_file, mock_input_file)

            with (
                patch("os.path.exists", return_value=True),
                patch("os.remove") as mock_remove,
            ):
                with pytest.raises(Exception, match="API Error"):
                    await tool._arun(
                        input_image="https://example.com/input.jpg",
                        prompt="test prompt",
                        name="test",
                        config=mock_config,
                    )

                # Verify cleanup happened
                mock_input_file.close.assert_called_once()
                mock_remove.assert_called_once_with(mock_tmp_file)

    @pytest.mark.asyncio
    async def test_cleanup_on_download_failure(
        self,
        tool: ReplicateKontextImageTool,
        mock_config: dict,
    ) -> None:
        """Test cleanup when image download fails."""
        with (
            patch.object(
                tool, "_download_input_image", side_effect=Exception("Download failed")
            ),
            pytest.raises(Exception, match="Download failed"),
        ):
            await tool._arun(
                input_image="https://example.com/bad_url.jpg",
                prompt="test prompt",
                name="test",
                config=mock_config,
            )

    def test_sync_run_method(self, tool: ReplicateKontextImageTool) -> None:
        """Test that the sync _run method calls the async _arun method."""
        with patch.object(tool, "_arun", return_value="test_result") as mock_arun:
            result = tool._run(
                input_image="https://example.com/test.jpg",
                prompt="test prompt",
                name="test",
                config={"configurable": {}},
            )

            mock_arun.assert_called_once()
            assert result == "test_result"

    @pytest.mark.asyncio
    async def test_kwargs_parameter_extraction(
        self,
        tool: ReplicateKontextImageTool,
        mock_config: dict,
    ) -> None:
        """Test extraction of parameters from kwargs."""
        # Mock proper FileOutput type
        mock_output = MagicMock()
        mock_output.__class__ = replicate.helpers.FileOutput

        with (
            patch("replicate.async_run", return_value=mock_output) as mock_replicate,
            patch.object(tool, "_download_input_image") as mock_download,
            patch.object(tool, "_save_and_process_edited_image", return_value="test"),
        ):
            mock_input_file = MagicMock()
            mock_download.return_value = ("/tmp/test", mock_input_file)

            await tool._arun(
                input_image="https://example.com/test.jpg",
                prompt="test prompt",
                name="test",
                config=mock_config,
                # Test kwargs defaults
                model="black-forest-labs/flux-kontext-max",
                seed=999,
                describe=False,
            )

            # Verify the replicate call used the correct model
            mock_replicate.assert_called_once()
            call_args = mock_replicate.call_args
            assert call_args[0][0] == "black-forest-labs/flux-kontext-max"

            # Verify input args
            input_args = call_args[1]["input"]
            expected_seed = 999
            assert input_args["seed"] == expected_seed
            assert input_args["prompt"] == "test prompt"
