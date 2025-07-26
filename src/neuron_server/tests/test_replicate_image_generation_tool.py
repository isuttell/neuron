"""Unit tests for the Replicate Image Generation Tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import replicate.helpers

from neuron_server.tools.replicate_image_generation_tool import (
    ReplicateImageGenerationTool,
    ReplicateImageGenerationToolArgs,
)


class TestReplicateImageGenerationTool:
    """Test suite for ReplicateImageGenerationTool."""

    def test_tool_args_schema(self) -> None:
        """Test that the tool args schema includes Google Imagen 4."""
        args = ReplicateImageGenerationToolArgs(
            name="Test Image",
            prompt="A beautiful sunset",
            model="google/imagen-4",
            aspect_ratio="16:9",
        )
        assert args.model == "google/imagen-4"
        assert args.aspect_ratio == "16:9"

    def test_prepare_input_args_google_imagen(self) -> None:
        """Test that Google Imagen 4 gets correct input arguments."""
        tool = ReplicateImageGenerationTool()

        input_args = tool._prepare_input_args(
            prompt="A beautiful sunset",
            model="google/imagen-4",
            aspect_ratio="16:9",
            num_inference_steps=25,
            image_options={},
        )

        # Google Imagen should only have these specific parameters
        assert input_args == {
            "prompt": "A beautiful sunset",
            "aspect_ratio": "16:9",
            "safety_filter_level": "block_only_high",
        }

        # Should not have parameters from other models
        assert "output_format" not in input_args
        assert "safety_tolerance" not in input_args
        assert "num_inference_steps" not in input_args

    def test_prepare_input_args_flux_model(self) -> None:
        """Test that Flux models get correct input arguments."""
        tool = ReplicateImageGenerationTool()

        input_args = tool._prepare_input_args(
            prompt="A beautiful sunset",
            model="black-forest-labs/flux-1.1-pro",
            aspect_ratio="16:9",
            num_inference_steps=25,
            image_options={"raw": True, "seed": 12345},
        )

        # Flux models should have standard parameters
        assert input_args["prompt"] == "A beautiful sunset"
        assert input_args["aspect_ratio"] == "16:9"
        assert input_args["output_format"] == "png"
        assert input_args["safety_tolerance"] == 6
        assert input_args["num_inference_steps"] == 25
        assert input_args["raw"] is True
        assert input_args["seed"] == 12345

        # Should not have Google-specific parameters
        assert "safety_filter_level" not in input_args

    def test_prepare_input_args_recraft_model(self) -> None:
        """Test that Recraft models get correct input arguments."""
        tool = ReplicateImageGenerationTool()

        input_args = tool._prepare_input_args(
            prompt="A beautiful sunset",
            model="recraft-ai/recraft-v3",
            aspect_ratio="16:9",
            num_inference_steps=25,
            image_options={"style": "realistic_image"},
        )

        # Recraft models should use size instead of aspect_ratio
        assert input_args["prompt"] == "A beautiful sunset"
        assert input_args["size"] == "1820x1024"  # 16:9 mapping
        assert "aspect_ratio" not in input_args
        assert input_args["style"] == "realistic_image"

    def test_tool_description_includes_google(self) -> None:
        """Test that the tool description mentions Google Imagen 4."""
        tool = ReplicateImageGenerationTool()
        assert "google/imagen-4" in tool.description
        assert "fine detail rendering" in tool.description

    @pytest.mark.asyncio
    @patch("neuron_server.tools.replicate_image_generation_tool.replicate.async_run")
    @patch("neuron_server.tools.replicate_image_generation_tool.describe_image")
    @patch("neuron_server.tools.replicate_image_generation_tool.aiofiles.open")
    @patch("neuron_server.tools.replicate_image_generation_tool.Image")
    @patch("neuron_server.tools.replicate_image_generation_tool.create_thumbnails")
    async def test_arun_with_google_imagen(
        self,
        mock_create_thumbnails: MagicMock,
        mock_image: MagicMock,
        mock_aiofiles_open: MagicMock,
        mock_describe_image: AsyncMock,
        mock_replicate_run: AsyncMock,
    ) -> None:
        """Test running the tool with Google Imagen 4."""

        # Create a proper mock for FileOutput that acts as an async iterator
        class MockFileOutput(replicate.helpers.FileOutput):
            def __init__(self) -> None:
                self.data = [b"fake_image_data"]
                self.url = "https://example.com/test.png"

            def __aiter__(self) -> "MockFileOutput":
                return self

            async def __anext__(self) -> bytes:
                if self.data:
                    return self.data.pop(0)
                raise StopAsyncIteration

        mock_file_output = MockFileOutput()
        mock_replicate_run.return_value = [mock_file_output]

        # Mock aiofiles.open
        mock_file_handle = AsyncMock()
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file_handle

        # Mock PIL Image
        mock_image_instance = MagicMock()
        mock_image_instance.save = MagicMock()
        mock_image.open.return_value = mock_image_instance

        mock_describe_image.return_value = MagicMock(
            description="A beautiful sunset",
            caption="Sunset",
            prompt_comparison="No differences",
        )

        tool = ReplicateImageGenerationTool()
        config = {"configurable": {"thread_id": "test-thread", "user_id": "test-user"}}

        result = await tool._arun(
            prompt="A beautiful sunset",
            name="Test Image",
            config=config,
            model="google/imagen-4",
            aspect_ratio="16:9",
            describe=False,
        )

        # Verify Replicate was called with correct arguments
        mock_replicate_run.assert_called_once_with(
            "google/imagen-4",
            input={
                "prompt": "A beautiful sunset",
                "aspect_ratio": "16:9",
                "safety_filter_level": "block_only_high",
            },
        )

        # Verify result format - should be tuple of (content, artifact)
        assert isinstance(result, tuple)
        assert len(result) == 2
        content, artifact = result

        # Check content (XML for LLM)
        assert "<image" in content
        assert "<id>" in content and "</id>" in content  # UUID generated dynamically

        # Check artifact (for UI) - it's returned as a list containing the artifact dict
        assert isinstance(artifact, list)
        assert len(artifact) == 1
        artifact_dict = artifact[0]
        assert isinstance(artifact_dict, dict)
        assert artifact_dict["type"] == "media"
        assert artifact_dict["media_type"] == "image"
        assert len(artifact_dict["items"]) == 1
        assert artifact_dict["items"][0]["id"] is not None  # UUID generated dynamically

        assert mock_file_handle.write.called
