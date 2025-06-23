"""Tests for message content processing functionality."""

from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from neuron_server.llms.message_processor import (
    MessageContentProcessor,
    get_message_content,
)


class MockMessage:
    """Mock message class for testing."""

    def __init__(self, content: str | list | None = None, **kwargs: Any) -> None:
        self.content = content


class TestMessageContentProcessor:
    """Test cases for MessageContentProcessor class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = MessageContentProcessor()

    def test_string_content_as_string(self) -> None:
        """Test processing string content with format_as_string=True."""
        message = MockMessage(content="Hello world")
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result == "Hello world"

    def test_string_content_as_structured(self) -> None:
        """Test processing string content with format_as_string=False."""
        message = MockMessage(content="Hello world")
        result = self.processor.get_message_content(message, format_as_string=False)
        expected = [{"type": "text", "text": "Hello world", "index": 0}]
        assert result == expected

    def test_empty_string_content(self) -> None:
        """Test handling of empty string content."""
        message = MockMessage(content="")
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result is None

    def test_none_content(self) -> None:
        """Test handling of None content."""
        message = MockMessage(content=None)
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result is None

    def test_list_content_with_strings_as_string(self) -> None:
        """Test processing list content containing strings, formatted as string."""
        content = ["First line", "Second line"]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result == "First line\nSecond line"

    def test_list_content_with_text_objects_as_string(self) -> None:
        """Test processing list content with text objects, formatted as string."""
        content = [
            {"type": "text", "text": "First line"},
            {"type": "text", "text": "Second line"},
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result == "First line\nSecond line"

    def test_list_content_mixed_as_string(self) -> None:
        """Test processing mixed list content, formatted as string."""
        content = [
            "Raw string",
            {"type": "text", "text": "Text object"},
            {"type": "tool_use", "name": "search", "input": {}},
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result == "Raw string\nText object\n[Tool: search]"

    def test_list_content_as_structured(self) -> None:
        """Test processing list content with format_as_string=False."""
        content = [
            "Raw string",
            {"type": "text", "text": "Text object"},
            {"type": "thinking", "thinking": "I need to think about this"},
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=False)

        expected = [
            {"type": "text", "text": "Raw string", "index": 0},
            {"type": "text", "text": "Text object", "index": 1},
            {"type": "thinking", "thinking": "I need to think about this", "index": 2},
        ]
        assert result == expected

    def test_tool_use_content_structured(self) -> None:
        """Test handling of tool_use content in structured format."""
        content = [
            {"type": "text", "text": "Let me search for that"},
            {
                "type": "tool_use",
                "id": "tool-123",
                "name": "web_search",
                "input": {"query": "python testing"},
            },
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=False)

        expected = [
            {"type": "text", "text": "Let me search for that", "index": 0},
            {
                "type": "tool_use",
                "id": "tool-123",
                "name": "web_search",
                "input": {"query": "python testing"},
                "index": 1,
            },
        ]
        assert result == expected

    def test_tool_use_content_as_string(self) -> None:
        """Test handling of tool_use content formatted as string."""
        content = [
            {"type": "text", "text": "Let me search"},
            {"type": "tool_use", "name": "web_search", "input": {"query": "test"}},
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result == "Let me search\n[Tool: web_search]"

    def test_thinking_content_structured(self) -> None:
        """Test handling of thinking content in structured format."""
        content = [
            {"type": "thinking", "thinking": "This is a complex problem"},
            {"type": "text", "text": "Here's my response"},
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=False)

        expected = [
            {"type": "thinking", "thinking": "This is a complex problem", "index": 0},
            {"type": "text", "text": "Here's my response", "index": 1},
        ]
        assert result == expected

    def test_custom_content_type_structured(self) -> None:
        """Test handling of unknown/custom content types in structured format."""
        content = [
            {
                "type": "custom_type",
                "custom_field": "custom_value",
                "data": {"key": "value"},
            }
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=False)

        expected = [
            {
                "type": "custom_type",
                "custom_field": "custom_value",
                "data": {"key": "value"},
                "index": 0,
            }
        ]
        assert result == expected

    def test_empty_list_content(self) -> None:
        """Test handling of empty list content."""
        message = MockMessage(content=[])
        result = self.processor.get_message_content(message, format_as_string=False)
        assert result is None

    def test_fallback_content_type_as_string(self) -> None:
        """Test fallback handling for non-string, non-list content as string."""
        message = MockMessage(content={"not": "supported"})
        result = self.processor.get_message_content(message, format_as_string=True)
        assert result == "{'not': 'supported'}"

    def test_fallback_content_type_structured(self) -> None:
        """Test fallback handling for non-string, non-list content as structured."""
        message = MockMessage(content=42)
        result = self.processor.get_message_content(message, format_as_string=False)
        expected = [{"type": "text", "text": "42", "index": 0}]
        assert result == expected

    def test_index_assignment(self) -> None:
        """Test that indices are assigned correctly in structured format."""
        content = [
            {"type": "text", "text": "First"},
            {"type": "thinking", "thinking": "Second"},
            {"type": "text", "text": "Third"},
        ]
        message = MockMessage(content=content)
        result = self.processor.get_message_content(message, format_as_string=False)

        assert result[0]["index"] == 0
        assert result[1]["index"] == 1
        assert result[2]["index"] == 2


class TestGlobalFunction:
    """Test cases for the global get_message_content function."""

    def test_global_function_backward_compatibility(self) -> None:
        """Test that the global function maintains backward compatibility."""
        message = AIMessage(content="Test message")
        result = get_message_content(message, format_as_string=True)
        assert result == "Test message"

    def test_global_function_structured_format(self) -> None:
        """Test global function with structured format."""
        message = HumanMessage(content="Test message")
        result = get_message_content(message, format_as_string=False)
        expected = [{"type": "text", "text": "Test message", "index": 0}]
        assert result == expected

    def test_global_function_with_complex_content(self) -> None:
        """Test global function with complex list content."""
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "tool_use", "name": "calculator", "input": {"expr": "2+2"}},
        ]
        message = AIMessage(content=content)
        result = get_message_content(message, format_as_string=True)
        assert result == "Hello\n[Tool: calculator]"

    def test_global_function_none_content(self) -> None:
        """Test global function with None content."""
        message = MockMessage(content=None)
        result = get_message_content(message)
        assert result is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
