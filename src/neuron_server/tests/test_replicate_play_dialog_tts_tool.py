from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.tools.replicate_play_dialog_tts_tool import (
    ReplicatePlayDialogTool,
)


class MockFileObject:
    """Mock file object that simulates Replicate's file output."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    def read(self) -> bytes:
        return self.content


class MockAsyncFileObject:
    """Mock async file object that simulates Replicate's async file output."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    async def read(self) -> bytes:
        return self.content


@pytest.fixture
def mock_config() -> RunnableConfig:
    """Create a mock RunnableConfig for testing."""
    return RunnableConfig(
        configurable={
            "thread_id": "test-thread-123",
            "user_id": "test-user-456",
        }
    )


@pytest.fixture
def tool() -> ReplicatePlayDialogTool:
    """Create a tool instance for testing."""
    return ReplicatePlayDialogTool()


@pytest.mark.asyncio
async def test_replicate_play_dialog_with_bytes_output(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test the tool with direct bytes output from Replicate."""
    test_audio_bytes = b"fake audio content"

    with (
        patch("replicate.async_run", new_callable=AsyncMock) as mock_run,
        patch("aiofiles.open", new_callable=MagicMock) as mock_aiofiles,
        patch(
            "neuron_server.models.media_item_model.MediaItemModel.create"
        ) as mock_create,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
        patch(
            "neuron_server.util.media_utilities.get_media_duration",
            new_callable=AsyncMock,
            return_value=7.8,
        ),
    ):
        # Configure the mocks
        mock_run.return_value = test_audio_bytes

        # Mock media item
        mock_media_item = MagicMock()
        mock_media_item.id = "media_123"
        mock_create.return_value = mock_media_item

        # Mock the async file context manager
        mock_file = AsyncMock()
        mock_aiofiles.return_value.__aenter__.return_value = mock_file

        # Run the tool
        result = await tool._arun(
            text="Hello, this is a test",
            name="test_audio",
            config=mock_config,
            voice="Angelo (Young male US conversational voice)",
            language="english",
        )

        # Verify the audio was written correctly
        mock_file.write.assert_called_once_with(test_audio_bytes)

        # Verify result format - should be tuple of (xml, artifact)
        assert isinstance(result, tuple)
        assert len(result) == 2
        xml_content, artifact = result

        # Check XML content
        assert "<audio>" in xml_content
        assert "<id>" in xml_content and "</id>" in xml_content  # UUID generated dynamically
        assert "<caption>test_audio</caption>" in xml_content

        # Check artifact - it's returned as a list containing the artifact dict
        assert isinstance(artifact, list)
        assert len(artifact) == 1
        artifact_dict = artifact[0]
        assert isinstance(artifact_dict, dict)
        assert artifact_dict["type"] == "media"
        assert artifact_dict["media_type"] == "audio"
        assert len(artifact_dict["items"]) == 1
        assert artifact_dict["items"][0]["id"] is not None  # UUID generated dynamically
        assert artifact_dict["items"][0]["caption"] == "test_audio"
        # Check that duration is from ffprobe
        assert artifact_dict["items"][0]["metadata"]["duration"] == 7.8


@pytest.mark.asyncio
async def test_replicate_play_dialog_with_file_object(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test the tool with file object output from Replicate."""
    test_audio_bytes = b"fake audio content from file"
    mock_file_obj = MockFileObject(test_audio_bytes)

    with (
        patch("replicate.async_run", new_callable=AsyncMock) as mock_run,
        patch("aiofiles.open", new_callable=MagicMock) as mock_aiofiles,
        patch(
            "neuron_server.models.media_item_model.MediaItemModel.create"
        ) as mock_create,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
        patch(
            "neuron_server.util.media_utilities.get_media_duration",
            new_callable=AsyncMock,
            return_value=7.8,
        ),
    ):
        # Configure the mocks
        mock_run.return_value = mock_file_obj

        # Mock media item
        mock_media_item = MagicMock()
        mock_media_item.id = "media_456"
        mock_create.return_value = mock_media_item

        # Mock the async file context manager
        mock_file = AsyncMock()
        mock_aiofiles.return_value.__aenter__.return_value = mock_file

        # Run the tool
        result = await tool._arun(
            text="Hello from file object",
            name="test_file_audio",
            config=mock_config,
        )

        # Verify the audio was written correctly
        mock_file.write.assert_called_once_with(test_audio_bytes)

        # Verify result is tuple
        assert isinstance(result, tuple)
        assert len(result) == 2


@pytest.mark.asyncio
async def test_replicate_play_dialog_with_async_file_object(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test the tool with async file object output from Replicate."""
    test_audio_bytes = b"fake audio content from async file"
    mock_file_obj = MockAsyncFileObject(test_audio_bytes)

    with (
        patch("replicate.async_run", new_callable=AsyncMock) as mock_run,
        patch("aiofiles.open", new_callable=MagicMock) as mock_aiofiles,
        patch(
            "neuron_server.models.media_item_model.MediaItemModel.create"
        ) as mock_create,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
        patch(
            "neuron_server.util.media_utilities.get_media_duration",
            new_callable=AsyncMock,
            return_value=7.8,
        ),
    ):
        # Configure the mocks
        mock_run.return_value = mock_file_obj

        # Mock media item
        mock_media_item = MagicMock()
        mock_media_item.id = "media_789"
        mock_create.return_value = mock_media_item

        # Mock the async file context manager
        mock_file = AsyncMock()
        mock_aiofiles.return_value.__aenter__.return_value = mock_file

        # Run the tool
        result = await tool._arun(
            text="Hello from async file object",
            name="test_async_file_audio",
            config=mock_config,
        )

        # Verify the audio was written correctly
        mock_file.write.assert_called_once_with(test_audio_bytes)

        # Verify result is tuple
        assert isinstance(result, tuple)
        assert len(result) == 2


@pytest.mark.asyncio
async def test_replicate_play_dialog_with_url_output(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test the tool with URL output from Replicate."""
    test_url = "https://example.com/audio.mp3"
    test_audio_bytes = b"fake audio content from URL"

    with (
        patch("replicate.async_run", new_callable=AsyncMock) as mock_run,
        patch("aiofiles.open", new_callable=MagicMock) as mock_aiofiles,
        patch(
            "neuron_server.tools.replicate_play_dialog_tts_tool.aiohttp.ClientSession"
        ) as mock_session_class,
        patch(
            "neuron_server.models.media_item_model.MediaItemModel.create"
        ) as mock_create,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
        patch(
            "neuron_server.util.media_utilities.get_media_duration",
            new_callable=AsyncMock,
            return_value=7.8,
        ),
    ):
        # Configure the mocks
        mock_run.return_value = test_url

        # Mock the async file context manager
        mock_file = AsyncMock()
        mock_aiofiles.return_value.__aenter__.return_value = mock_file

        # Mock the aiohttp session and response
        mock_response = AsyncMock()
        mock_response.read = AsyncMock(return_value=test_audio_bytes)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        # Mock media item
        mock_media_item = MagicMock()
        mock_media_item.id = "media_url_123"
        mock_create.return_value = mock_media_item

        # Run the tool
        result = await tool._arun(
            text="Hello from URL",
            name="test_url_audio",
            config=mock_config,
        )

        # Verify the URL was fetched
        mock_session.get.assert_called_once_with(test_url)

        # Verify the audio was written correctly
        mock_file.write.assert_called_once_with(test_audio_bytes)

        # Verify result is tuple
        assert isinstance(result, tuple)
        assert len(result) == 2


@pytest.mark.asyncio
async def test_replicate_play_dialog_with_unexpected_output(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test the tool with unexpected output type from Replicate."""
    unexpected_output = {"some": "dict"}

    with (
        patch("replicate.async_run", new_callable=AsyncMock) as mock_run,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
    ):
        # Configure the mocks
        mock_run.return_value = unexpected_output

        # Run the tool and expect an error
        with pytest.raises(ValueError) as exc_info:
            await tool._arun(
                text="This should fail",
                name="test_fail",
                config=mock_config,
            )

        assert "Unexpected output type from Replicate" in str(exc_info.value)
        assert "dict" in str(exc_info.value)


@pytest.mark.asyncio
async def test_replicate_play_dialog_with_custom_parameters(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test the tool with custom voice parameters."""
    test_audio_bytes = b"fake audio with custom params"

    with (
        patch("replicate.async_run", new_callable=AsyncMock) as mock_run,
        patch("aiofiles.open", new_callable=MagicMock) as mock_aiofiles,
        patch(
            "neuron_server.models.media_item_model.MediaItemModel.create"
        ) as mock_create,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
        patch(
            "neuron_server.util.media_utilities.get_media_duration",
            new_callable=AsyncMock,
            return_value=7.8,
        ),
    ):
        # Configure the mocks
        mock_run.return_value = test_audio_bytes

        # Mock media item
        mock_media_item = MagicMock()
        mock_media_item.id = "media_custom_123"
        mock_create.return_value = mock_media_item

        # Mock the async file context manager
        mock_file = AsyncMock()
        mock_aiofiles.return_value.__aenter__.return_value = mock_file

        # Run the tool with custom parameters
        result = await tool._arun(
            text="Hello with custom voice",
            name="test_custom",
            config=mock_config,
            voice="Angelo (Young male US conversational voice)",
            language="english",
            temperature=1.2,
            seed=12345,
        )

        # Verify the replicate API was called with correct parameters
        mock_run.assert_called_once()
        call_args = mock_run.call_args[1]["input"]
        assert call_args["text"] == "Hello with custom voice"
        assert call_args["voice"] == "Angelo (Young male US conversational voice)"
        assert call_args["language"] == "english"
        assert call_args["temperature"] == 1.2
        assert call_args["seed"] == 12345

        # Verify result is tuple
        assert isinstance(result, tuple)
        assert len(result) == 2


@pytest.mark.asyncio
async def test_replicate_play_dialog_error_handling(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test error handling in the tool."""
    with (
        patch("replicate.async_run", new_callable=AsyncMock) as mock_run,
        patch("os.path.exists", return_value=True),
        patch("os.makedirs"),
    ):
        # Configure the mock to raise an exception
        mock_run.side_effect = Exception("Replicate API error")

        # Run the tool and expect the exception to propagate
        with pytest.raises(Exception) as exc_info:
            await tool._arun(
                text="This should fail",
                name="test_error",
                config=mock_config,
            )

        assert "Replicate API error" in str(exc_info.value)


def test_sync_run_method(
    tool: ReplicatePlayDialogTool, mock_config: RunnableConfig
) -> None:
    """Test the synchronous _run method."""
    with patch.object(tool, "_arun", new_callable=AsyncMock) as mock_arun:
        mock_arun.return_value = "http://example.com/audio.mp3"

        result = tool._run(
            text="Test sync run",
            name="test_sync",
            config=mock_config,
        )

        assert result == "http://example.com/audio.mp3"
        mock_arun.assert_called_once_with(
            text="Test sync run",
            name="test_sync",
            config=mock_config,
        )
