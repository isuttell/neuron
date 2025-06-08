from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from neuron_server.llms.anthropic import AnthropicLLM
from neuron_server.llms.llm import THINKING_TOKEN_BUDGETS


class TestAnthropicCaching:
    """Test suite for Anthropic LLM caching functionality."""

    def test_init_with_caching_enabled(self) -> None:
        """Test that AnthropicLLM can be initialized with caching enabled."""
        llm = AnthropicLLM(caching_enabled=True)
        assert llm.caching_enabled is True

    def test_init_with_caching_disabled(self) -> None:
        """Test that AnthropicLLM defaults to caching disabled."""
        llm = AnthropicLLM(caching_enabled=False)
        assert llm.caching_enabled is False

    def test_init_default_caching(self) -> None:
        """Test that AnthropicLLM defaults to caching disabled."""
        llm = AnthropicLLM()
        assert llm.caching_enabled is False

    def test_apply_caching_string_content(self) -> None:
        """Test that cache control is added to string content."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            HumanMessage(content="Hello, world!"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="How are you?"),
        ]

        result = llm._apply_caching_to_messages(messages)

        # Should add cache control to the last human message
        expected_message_count = 3
        assert len(result) == expected_message_count
        last_message = result[-1]
        assert isinstance(last_message, HumanMessage)
        assert isinstance(last_message.content, list)
        expected_content_blocks = 1
        assert len(last_message.content) == expected_content_blocks
        assert last_message.content[0]["type"] == "text"
        assert last_message.content[0]["text"] == "How are you?"
        assert last_message.content[0]["cache_control"] == {"type": "ephemeral"}

    def test_apply_caching_list_content(self) -> None:
        """Test that cache control is added to list content."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            HumanMessage(content="Hello, world!"),
            AIMessage(content="Hi there!"),
            HumanMessage(
                content=[
                    {"type": "text", "text": "How are you today?"},
                    {"type": "text", "text": "I hope you're doing well."},
                ]
            ),
        ]

        result = llm._apply_caching_to_messages(messages)

        # Should add cache control only to the last content block
        expected_message_count = 3
        assert len(result) == expected_message_count
        last_message = result[-1]
        assert isinstance(last_message, HumanMessage)
        assert isinstance(last_message.content, list)
        expected_content_blocks = 2
        assert len(last_message.content) == expected_content_blocks

        # First content block should not have cache control
        assert last_message.content[0]["type"] == "text"
        assert last_message.content[0]["text"] == "How are you today?"
        assert "cache_control" not in last_message.content[0]

        # Second (last) content block should have cache control
        assert last_message.content[1]["type"] == "text"
        assert last_message.content[1]["text"] == "I hope you're doing well."
        assert last_message.content[1]["cache_control"] == {"type": "ephemeral"}

    def test_apply_caching_no_human_messages(self) -> None:
        """Test behavior when there are no human messages."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            AIMessage(content="Hi there!"),
            AIMessage(content="How can I help you?"),
        ]

        result = llm._apply_caching_to_messages(messages)

        # Should return unchanged since no human messages
        expected_message_count = 2
        assert len(result) == expected_message_count
        assert all(isinstance(msg, AIMessage) for msg in result)

    def test_apply_caching_finds_last_human_message(self) -> None:
        """Test that cache control is added to the last human message."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            HumanMessage(content="First question"),
            AIMessage(content="First response"),
            HumanMessage(content="Second question"),
            AIMessage(content="Second response"),
        ]

        result = llm._apply_caching_to_messages(messages)

        # Should add cache control to the last human message (index 2)
        expected_message_count = 4
        assert len(result) == expected_message_count

        # First human message should be unchanged
        assert result[0].content == "First question"
        assert isinstance(result[0].content, str)

        # Last human message should have cache control
        last_human_message = result[2]
        assert isinstance(last_human_message, HumanMessage)
        assert isinstance(last_human_message.content, list)
        assert last_human_message.content[0]["text"] == "Second question"
        cache_control = {"type": "ephemeral"}
        assert last_human_message.content[0]["cache_control"] == cache_control

        # AI messages should be unchanged
        assert isinstance(result[1], AIMessage)
        assert isinstance(result[3], AIMessage)

    def test_apply_caching_preserves_message_attributes(self) -> None:
        """Test that other message attributes are preserved."""
        llm = AnthropicLLM(caching_enabled=True)
        original_message = HumanMessage(
            content="Test message",
            id="test-id-123",
            additional_kwargs={"key": "value"},
        )
        messages = [original_message]

        result = llm._apply_caching_to_messages(messages)

        modified_message = result[0]
        assert modified_message.id == "test-id-123"
        assert modified_message.additional_kwargs == {"key": "value"}
        assert isinstance(modified_message.content, list)
        assert modified_message.content[0]["text"] == "Test message"
        assert modified_message.content[0]["cache_control"] == {"type": "ephemeral"}

    def test_apply_caching_empty_messages(self) -> None:
        """Test behavior with empty message list."""
        llm = AnthropicLLM(caching_enabled=True)
        messages: list[Any] = []

        result = llm._apply_caching_to_messages(messages)

        assert len(result) == 0

    def test_apply_caching_mixed_content_types(self) -> None:
        """Test handling of mixed content types in list."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": "Here's some text"},
                    "string content",  # Non-dict content
                    {"type": "image_url", "image_url": {"url": "https://example.com"}},
                ]
            ),
        ]

        result = llm._apply_caching_to_messages(messages)

        modified_message = result[0]
        assert isinstance(modified_message.content, list)
        expected_content_blocks = 3
        assert len(modified_message.content) == expected_content_blocks

        # First block should be unchanged
        assert modified_message.content[0]["type"] == "text"
        assert "cache_control" not in modified_message.content[0]

        # Second block (string) should be unchanged
        assert modified_message.content[1] == "string content"

        # Last block should have cache control added
        assert modified_message.content[2]["type"] == "image_url"
        assert modified_message.content[2]["cache_control"] == {"type": "ephemeral"}

    def test_apply_caching_empty_list_content(self) -> None:
        """Test behavior when message has empty list content."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            HumanMessage(content=[]),
        ]

        result = llm._apply_caching_to_messages(messages)

        # Should return unchanged since content list is empty
        assert len(result) == 1
        assert result[0].content == []

    def test_apply_caching_empty_string_content(self) -> None:
        """Test behavior when message has empty string content."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            HumanMessage(content=""),
        ]

        result = llm._apply_caching_to_messages(messages)

        # Should add cache control even for empty string
        assert len(result) == 1
        assert isinstance(result[0].content, list)
        assert len(result[0].content) == 1
        assert result[0].content[0]["text"] == ""
        assert result[0].content[0]["cache_control"] == {"type": "ephemeral"}

    def test_apply_caching_maintains_message_order(self) -> None:
        """Test that message order is preserved."""
        llm = AnthropicLLM(caching_enabled=True)
        messages = [
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
            HumanMessage(content="Message 2"),
            AIMessage(content="Response 2"),
            HumanMessage(content="Message 3"),
        ]

        result = llm._apply_caching_to_messages(messages)

        # Check that order is maintained
        expected_message_count = 5
        assert len(result) == expected_message_count
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)
        assert isinstance(result[2], HumanMessage)
        assert isinstance(result[3], AIMessage)
        assert isinstance(result[4], HumanMessage)

        # Only the last human message should have cache control
        assert isinstance(result[0].content, str)  # Unchanged
        assert isinstance(result[2].content, str)  # Unchanged
        assert isinstance(result[4].content, list)  # Modified with cache control

    def test_create_model_with_thinking_off(self) -> None:
        """Test model creation with thinking off."""
        llm = AnthropicLLM(
            model_id="claude-3-5-sonnet-20241022",
            provider_model_id="claude-sonnet-4-20250514",
        )

        # Test with empty tools - should return base model
        result = llm._create_model_with_thinking("off", [])
        assert result == llm.model

        # Test with None tools - should return base model
        result_none = llm._create_model_with_thinking("off", None)
        assert result_none == llm.model

    def test_create_model_with_thinking_low(self) -> None:
        """Test model creation with thinking level low."""
        from unittest.mock import MagicMock, patch

        llm = AnthropicLLM(
            model_id="claude-3-5-sonnet-20241022",
            provider_model_id="claude-sonnet-4-20250514",
        )

        tools = [MagicMock()]

        with patch("neuron_server.llms.anthropic.ChatAnthropic") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.bind_tools = MagicMock(return_value=mock_instance)
            mock_chat.return_value = mock_instance

            llm._create_model_with_thinking("low", tools)

            # Verify ChatAnthropic was called with thinking config
            expected_params = llm.model_params.copy()
            expected_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": THINKING_TOKEN_BUDGETS["low"],
            }
            mock_chat.assert_called_once_with(**expected_params)
            mock_instance.bind_tools.assert_called_once_with(tools)

    def test_create_model_with_thinking_medium(self) -> None:
        """Test model creation with thinking level medium."""
        from unittest.mock import MagicMock, patch

        llm = AnthropicLLM(
            model_id="claude-3-5-sonnet-20241022",
            provider_model_id="claude-opus-4-20250514",
        )

        tools = [MagicMock()]

        with patch("neuron_server.llms.anthropic.ChatAnthropic") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.bind_tools = MagicMock(return_value=mock_instance)
            mock_chat.return_value = mock_instance

            llm._create_model_with_thinking("medium", tools)

            # Verify ChatAnthropic was called with thinking config
            expected_params = llm.model_params.copy()
            expected_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": THINKING_TOKEN_BUDGETS["medium"],
            }
            mock_chat.assert_called_once_with(**expected_params)
            mock_instance.bind_tools.assert_called_once_with(tools)

    def test_model_params_stored_correctly(self) -> None:
        """Test that model parameters are stored correctly for dynamic instantiation."""
        llm = AnthropicLLM(
            model_id="claude-3-5-sonnet-20241022",
            provider_model_id="claude-sonnet-4-20250514",
        )

        assert llm.model_params["model"] == "claude-3-5-sonnet-20241022"
        assert llm.model_params["temperature"] == 1
        assert llm.model_params["streaming"] is True
        assert llm.model_params["max_tokens"] == 64_000
        assert llm.model_params["verbose"] is True
        assert "thinking" not in llm.model_params  # No thinking in default params

    def test_create_model_with_thinking_empty_tools(self) -> None:
        """Test model creation with empty tools list."""

        llm = AnthropicLLM(
            model_id="claude-3-5-sonnet-20241022",
            provider_model_id="claude-sonnet-4-20250514",
        )

        tools = []

        # Test with "off" - should return model without binding
        result = llm._create_model_with_thinking("off", tools)
        # Should return base model without binding empty tools
        assert result == llm.model
