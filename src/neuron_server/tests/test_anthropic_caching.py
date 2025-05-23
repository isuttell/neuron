from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from neuron_server.llms.anthropic import AnthropicLLM


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
            HumanMessage(content=[
                {"type": "text", "text": "How are you today?"},
                {"type": "text", "text": "I hope you're doing well."},
            ]),
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
            HumanMessage(content=[
                {"type": "text", "text": "Here's some text"},
                "string content",  # Non-dict content
                {"type": "image_url", "image_url": {"url": "https://example.com"}},
            ]),
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
