"""Unit tests for ElevenLabs TTS tool."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.tools.elevenlabs_tts_tool import ElevenLabsTTSTool, VoiceLine


class TestElevenLabsTTSTool:
    """Test suite for ElevenLabs TTS tool."""

    @pytest.fixture
    def tool(self) -> ElevenLabsTTSTool:
        """Create an ElevenLabs TTS tool instance."""
        return ElevenLabsTTSTool()

    @pytest.fixture
    def mock_config(self) -> RunnableConfig:
        """Create a mock RunnableConfig."""
        return {"configurable": {"user_id": "test_user_123"}}

    @pytest.fixture
    def sample_script(self) -> list[VoiceLine]:
        """Create a sample script with voice lines."""
        return [
            VoiceLine(voice="Aria", text="Hello, this is a test."),
            VoiceLine(voice="Callum", text="Testing the ElevenLabs API."),
        ]

    @pytest.mark.asyncio
    async def test_get_voice_mappings_success(self, tool: ElevenLabsTTSTool) -> None:
        """Test successful voice mapping retrieval from API."""
        mock_client = AsyncMock()
        mock_voice1 = MagicMock()
        mock_voice1.name = "Aria"
        mock_voice1.voice_id = "aria_id_123"
        mock_voice2 = MagicMock()
        mock_voice2.name = "Callum"
        mock_voice2.voice_id = "callum_id_456"
        mock_response = MagicMock(voices=[mock_voice1, mock_voice2])
        mock_client.voices.get_all.return_value = mock_response

        voice_map = await tool._get_voice_mappings(mock_client)

        assert voice_map == {"Aria": "aria_id_123", "Callum": "callum_id_456"}
        mock_client.voices.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_voice_mappings_api_failure(
        self, tool: ElevenLabsTTSTool
    ) -> None:
        """Test voice mapping when API call fails."""
        mock_client = AsyncMock()
        mock_client.voices.get_all.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError) as exc_info:
            await tool._get_voice_mappings(mock_client)

        assert "Unable to retrieve voice list from ElevenLabs API" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_arun_voice_not_found(
        self, tool: ElevenLabsTTSTool, mock_config: RunnableConfig
    ) -> None:
        """Test error when requested voice is not found in mappings."""
        # Use a valid voice name that won't be in the mocked API response
        script = [VoiceLine(voice="Callum", text="Test")]

        with patch(
            "neuron_server.tools.elevenlabs_tts_tool.AsyncElevenLabs"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful API call but requested voice not in list
            mock_voice = MagicMock()
            mock_voice.name = "Aria"
            mock_voice.voice_id = "aria_id_123"
            mock_response = MagicMock(voices=[mock_voice])
            mock_client.voices.get_all.return_value = mock_response

            with pytest.raises(ValueError) as exc_info:
                await tool._arun(script, "test_audio", mock_config)

            assert "Voice 'Callum' not found in ElevenLabs voice list" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_arun_successful_generation(
        self,
        tool: ElevenLabsTTSTool,
        mock_config: RunnableConfig,
        sample_script: list[VoiceLine],
    ) -> None:
        """Test successful audio generation with new API."""
        base_path = "neuron_server.tools.elevenlabs_tts_tool"
        with patch(f"{base_path}.AsyncElevenLabs") as mock_client_class, \
             patch(f"{base_path}.os.makedirs"), \
             patch(f"{base_path}.shutil.rmtree"), \
             patch(f"{base_path}.shutil.copy"), \
             patch(f"{base_path}.run_subprocess"), \
             patch(f"{base_path}.MediaItemModel") as mock_media_model, \
             patch(f"{base_path}.neuron_config") as mock_config_obj:

            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock voice mappings
            mock_voice1 = MagicMock()
            mock_voice1.name = "Aria"
            mock_voice1.voice_id = "aria_id_123"
            mock_voice2 = MagicMock()
            mock_voice2.name = "Callum"
            mock_voice2.voice_id = "callum_id_456"
            mock_response = MagicMock(voices=[mock_voice1, mock_voice2])
            mock_client.voices.get_all.return_value = mock_response

            # Mock audio stream
            async def mock_stream_generator() -> AsyncIterator[bytes]:
                yield b"audio_chunk_1"
                yield b"audio_chunk_2"

            mock_client.text_to_speech.stream.return_value = mock_stream_generator()

            # Mock config
            mock_config_obj.elevenlabs_api_key = "test_api_key"
            mock_config_obj.temp_folder = "/tmp"
            mock_config_obj.static_folder = "/static"
            mock_config_obj.static_content_url = "http://localhost/static"

            # Mock media item creation
            mock_media_item = MagicMock(id="media_123")
            mock_media_model.create = AsyncMock(return_value=mock_media_item)

            # Mock file operations
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file

                result = await tool._arun(sample_script, "test_audio", mock_config)

            # Verify API calls
            expected_calls = 2
            assert mock_client.text_to_speech.stream.call_count == expected_calls

            # Check first call
            first_call = mock_client.text_to_speech.stream.call_args_list[0]
            assert first_call.kwargs["text"] == "Hello, this is a test."
            assert first_call.kwargs["voice_id"] == "aria_id_123"
            assert first_call.kwargs["model_id"] == "eleven_turbo_v2_5"

            # Check second call
            second_call = mock_client.text_to_speech.stream.call_args_list[1]
            assert second_call.kwargs["text"] == "Testing the ElevenLabs API."
            assert second_call.kwargs["voice_id"] == "callum_id_456"

            # Verify result format
            assert '<audio id="media_123">' in result
            assert '<audio src="http://localhost/static/' in result

    @pytest.mark.asyncio
    async def test_arun_empty_script(
        self, tool: ElevenLabsTTSTool, mock_config: RunnableConfig
    ) -> None:
        """Test error when script is empty."""
        base_path = "neuron_server.tools.elevenlabs_tts_tool"
        with patch(f"{base_path}.AsyncElevenLabs") as mock_client_class, \
             patch(f"{base_path}.neuron_config") as mock_config_obj:

            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_config_obj.elevenlabs_api_key = "test_api_key"

            # Mock voice mappings (even though we won't use them)
            mock_response = MagicMock(voices=[])
            mock_client.voices.get_all.return_value = mock_response

            with pytest.raises(ValueError) as exc_info:
                await tool._arun([], "test_audio", mock_config)

            assert "Failed to parse script. Found no lines." in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_arun_with_multilingual_model(
        self,
        tool: ElevenLabsTTSTool,
        mock_config: RunnableConfig,
    ) -> None:
        """Test audio generation with multilingual model."""
        script = [VoiceLine(voice="Aria", text="Test multilingual")]

        base_path = "neuron_server.tools.elevenlabs_tts_tool"
        with patch(f"{base_path}.AsyncElevenLabs") as mock_client_class, \
             patch(f"{base_path}.os.makedirs"), \
             patch(f"{base_path}.shutil.rmtree"), \
             patch(f"{base_path}.shutil.copy"), \
             patch(f"{base_path}.run_subprocess"), \
             patch(f"{base_path}.MediaItemModel") as mock_media_model, \
             patch(f"{base_path}.neuron_config") as mock_config_obj:

            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock voice mappings
            mock_voice = MagicMock()
            mock_voice.name = "Aria"
            mock_voice.voice_id = "aria_id_123"
            mock_response = MagicMock(voices=[mock_voice])
            mock_client.voices.get_all.return_value = mock_response

            # Mock audio stream
            async def mock_stream_generator() -> AsyncIterator[bytes]:
                yield b"audio_data"

            mock_client.text_to_speech.stream.return_value = mock_stream_generator()

            # Mock config
            mock_config_obj.elevenlabs_api_key = "test_api_key"
            mock_config_obj.temp_folder = "/tmp"
            mock_config_obj.static_folder = "/static"
            mock_config_obj.static_content_url = "http://localhost/static"

            # Mock media item creation
            mock_media_item = MagicMock(id="media_456")
            mock_media_model.create = AsyncMock(return_value=mock_media_item)

            with patch("builtins.open", create=True):
                await tool._arun(
                    script, "test_audio", mock_config, model="eleven_multilingual_v2"
                )

            # Verify multilingual model was used
            call_args = mock_client.text_to_speech.stream.call_args
            assert call_args.kwargs["model_id"] == "eleven_multilingual_v2"
