"""Message content processing functionality."""

from typing import Any

from langchain_core.messages import BaseMessage


class MessageContentProcessor:
    """Handles message content processing and formatting."""

    @staticmethod
    def _process_string_content(
        content: str, format_as_string: bool
    ) -> str | list[dict[str, Any]]:
        """Process string content based on format preference."""
        if format_as_string:
            return content
        return [{"type": "text", "text": content, "index": 0}]

    @staticmethod
    def _process_list_content_as_string(content: list) -> str:
        """Process list content and return as a string."""
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                part_type = part.get("type")
                if part_type == "text":
                    text_parts.append(part.get("text", ""))
                elif part_type == "tool_use":
                    # Include tool use in string representation
                    tool_name = part.get("name", "unknown_tool")
                    text_parts.append(f"[Tool: {tool_name}]")
        return "\n".join(text_parts)

    @staticmethod
    def _process_list_content_as_structured(
        content: list,
    ) -> list[dict[str, Any]] | None:
        """Process list content and return as structured content."""
        contents = []
        index = 0
        for part in content:
            if isinstance(part, str):
                contents.append({"type": "text", "text": part, "index": index})
                index += 1
            elif isinstance(part, dict):
                content_type = part.get("type")
                if content_type == "text":
                    contents.append(
                        {"type": "text", "text": part.get("text", ""), "index": index}
                    )
                    index += 1
                elif content_type == "thinking":
                    contents.append(
                        {
                            "type": "thinking",
                            "thinking": part.get("thinking", ""),
                            "index": index,
                        }
                    )
                    index += 1
                elif content_type == "tool_use":
                    # Handle tool use content
                    contents.append(
                        {
                            "type": "tool_use",
                            "id": part.get("id", ""),
                            "name": part.get("name", ""),
                            "input": part.get("input", {}),
                            "index": index,
                        }
                    )
                    index += 1
                else:
                    # Handle any other content types generically
                    # Copy all fields from the original part
                    generic_content = {"index": index}
                    generic_content.update(part)
                    contents.append(generic_content)
                    index += 1
        return contents if contents else None

    def get_message_content(
        self, message: BaseMessage, format_as_string: bool = False
    ) -> list[dict[str, Any]] | str | None:
        """Extract the content from a message and format it for display.

        Args:
            message: The message to extract content from
            format_as_string: If True, return content as a string
                (for backward compatibility)

        Returns:
            A list of content objects, a string, or None if no content
        """
        if not message.content:
            return None

        content = message.content

        # Process string content
        if isinstance(content, str):
            return self._process_string_content(content, format_as_string)

        # Process list content
        if isinstance(content, list):
            if format_as_string:
                return self._process_list_content_as_string(content)
            return self._process_list_content_as_structured(content)

        # Fallback for other content types
        if format_as_string:
            return str(content)
        return [{"type": "text", "text": str(content), "index": 0}]


# Global instance for backward compatibility
_processor = MessageContentProcessor()


def get_message_content(
    message: BaseMessage, format_as_string: bool = False
) -> list[dict[str, Any]] | str | None:
    """Extract the content from a message and format it for display.

    Args:
        message: The message to extract content from
        format_as_string: If True, return content as a string
            (for backward compatibility)

    Returns:
        A list of content objects, a string, or None if no content
    """
    return _processor.get_message_content(message, format_as_string)
