from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from neuron_server.tools.replicate_kokoro_tts_tool import (
    DEFAULT_TEXT_PREVIEW_LENGTH,
    ReplicateKokoroTTSTool,
    ReplicateKokoroTTSToolArgs,
    create_text_preview,
)


class TestReplicateKokoroTTSTool:
    def test_tool_initialization(self):
        """Test that the tool can be initialized correctly."""
        tool = ReplicateKokoroTTSTool()
        assert tool.name == "replicate_kokoro_tts"
        assert "Kokoro" in tool.description
        assert tool.args_schema == ReplicateKokoroTTSToolArgs

    def test_args_schema_validation(self):
        """Test that the args schema validates correctly."""
        # Valid args
        args = ReplicateKokoroTTSToolArgs(
            name="test", text="Hello world", voice="af_bella", speed=1.0
        )
        assert args.name == "test"
        assert args.text == "Hello world"
        assert args.voice == "af_bella"
        assert args.speed == 1.0

    def test_args_schema_defaults(self):
        """Test that default values are set correctly."""
        args = ReplicateKokoroTTSToolArgs(name="test", text="Hello world")
        assert args.voice == "af_bella"
        assert args.speed == 1.0

    def test_speed_validation(self):
        """Test speed parameter validation."""
        # Valid speeds
        for speed in [0.1, 1.0, 2.0, 5.0]:
            args = ReplicateKokoroTTSToolArgs(
                name="test", text="Hello world", speed=speed
            )
            assert args.speed == speed

        # Invalid speeds should raise validation error
        with pytest.raises(ValueError):
            ReplicateKokoroTTSToolArgs(
                name="test",
                text="Hello world",
                speed=0.05,  # Below minimum
            )

        with pytest.raises(ValueError):
            ReplicateKokoroTTSToolArgs(
                name="test",
                text="Hello world",
                speed=6.0,  # Above maximum
            )

    def test_voice_validation(self):
        """Test voice parameter validation."""
        # Valid voices
        valid_voices = ["af_bella", "am_fenrir", "bf_emma", "af_nicole"]
        for voice in valid_voices:
            args = ReplicateKokoroTTSToolArgs(
                name="test", text="Hello world", voice=voice
            )
            assert args.voice == voice

    @patch("neuron_server.tools.replicate_kokoro_tts_tool.replicate.async_run")
    @patch("neuron_server.tools.replicate_kokoro_tts_tool.save_replicate_output")
    @patch(
        "neuron_server.util.media_utilities.get_media_duration",
        new_callable=AsyncMock,
        return_value=5.2,
    )
    async def test_arun_bytes_output(
        self, mock_duration, mock_save_output, mock_replicate
    ):
        """Test the basic flow of the _arun method with bytes output."""
        # Mock replicate response as bytes (simpler case)
        mock_replicate.return_value = b"fake audio data"


        # Mock config
        config = {"configurable": {"thread_id": "test-thread", "user_id": "test-user"}}

        tool = ReplicateKokoroTTSTool()

        result = await tool._arun(
            text="Hello world",
            name="test audio",
            config=config,
            voice="af_bella",
            speed=1.0,
        )

        # Verify replicate was called with correct parameters
        mock_replicate.assert_called_once()
        call_args = mock_replicate.call_args
        assert call_args[0][0] == tool.ref
        assert call_args[1]["input"]["text"] == "Hello world"
        assert call_args[1]["input"]["voice"] == "af_bella"
        assert call_args[1]["input"]["speed"] == 1.0

        # Verify save_replicate_output was called
        mock_save_output.assert_called_once()

        # Verify result format - should be tuple of (xml, artifact)
        assert isinstance(result, tuple)
        assert len(result) == 2
        xml_content, artifact = result

        # Check XML content
        assert "<audio>" in xml_content
        assert "<id>" in xml_content and "</id>" in xml_content  # UUID generated dynamically
        assert "<caption>test audio</caption>" in xml_content

        # Check artifact - it's returned as a list containing the artifact dict
        assert isinstance(artifact, list)
        assert len(artifact) == 1
        artifact_dict = artifact[0]
        assert isinstance(artifact_dict, dict)
        assert artifact_dict["type"] == "media"
        assert artifact_dict["media_type"] == "audio"
        assert len(artifact_dict["items"]) == 1
        assert artifact_dict["items"][0]["id"] is not None  # UUID generated dynamically
        assert artifact_dict["items"][0]["caption"] == "test audio"
        # Check that duration is from ffprobe
        assert artifact_dict["items"][0]["metadata"]["duration"] == 5.2

    def test_create_text_preview_short_text(self):
        """Test text preview with short text."""
        short_text = "Hello world"
        assert create_text_preview(short_text) == "Hello world"

    def test_create_text_preview_long_text(self):
        """Test text preview with long text."""
        long_text = "a" * 150
        preview = create_text_preview(long_text)
        assert len(preview) == DEFAULT_TEXT_PREVIEW_LENGTH + 3  # +3 for "..."
        assert preview.endswith("...")
        assert preview.startswith("a" * DEFAULT_TEXT_PREVIEW_LENGTH)

    def test_create_text_preview_custom_length(self):
        """Test text preview with custom max length."""
        text = "a" * 50
        preview = create_text_preview(text, max_length=20)
        assert len(preview) == 23  # 20 + 3 for "..."
        assert preview == "a" * 20 + "..."

    def test_create_text_preview_exact_length(self):
        """Test text preview with text exactly at max length."""
        text = "a" * DEFAULT_TEXT_PREVIEW_LENGTH
        preview = create_text_preview(text)
        assert preview == text
        assert not preview.endswith("...")
