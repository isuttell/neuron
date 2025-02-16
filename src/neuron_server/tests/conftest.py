from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage
from pytest import MonkeyPatch

from neuron_server.config import Config


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch: MonkeyPatch) -> None:
    """Mock environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-api-key")


@pytest.fixture
def mock_config() -> None:
    """Mock configuration for testing."""
    with patch("neuron_server.config.config", Config()):
        yield


@pytest.fixture
def mock_ai_message() -> AIMessage:
    """Create a mock AI message for testing."""
    return AIMessage(
        content="Test response",
        tool_calls=[],
        created_at="2024-02-16T13:00:00-08:00",
    )


@pytest.fixture
def mock_openai() -> None:
    """Mock OpenAI client for testing."""
    with patch("openai.OpenAI") as mock:
        mock.return_value.chat.completions.create.return_value = {
            "choices": [{"message": {"content": "Test response", "tool_calls": []}}]
        }
        yield mock
