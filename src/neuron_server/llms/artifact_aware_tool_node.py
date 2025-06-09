"""Custom ToolNode implementation that properly handles tool artifacts.

This module provides an enhanced ToolNode that ensures tools returning artifacts
(via response_format="content_and_artifact") have their artifacts properly
captured and passed through to ToolMessages.
"""

from typing import Literal, Union, cast

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphBubbleUp
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import (
    ToolCall,
    _handle_tool_error,
    _infer_handled_types,
    msg_content_output,
)


class ArtifactAwareToolNode(ToolNode):
    """Custom ToolNode that ensures proper handling of tool artifacts.

    This node extends the standard ToolNode to properly handle tools that
    return artifacts via response_format="content_and_artifact". The standard
    ToolNode may not properly propagate artifacts from tools to ToolMessages,
    so this implementation ensures artifacts are captured and passed through.
    """

    def _run_one(
        self,
        call: ToolCall,
        input_type: Literal["list", "dict", "tool_calls"],
        config: RunnableConfig,
    ) -> ToolMessage:
        """Run a single tool synchronously, ensuring artifact handling.

        This method overrides the parent implementation to ensure that when
        tools return ToolMessages with artifacts, those artifacts are preserved.
        """
        # Validate the tool call first
        if invalid_tool_message := self._validate_tool_call(call):
            return invalid_tool_message

        try:
            # Prepare the input - ToolNode passes the full call dict
            input_dict = {**call, **{"type": "tool_call"}}

            # Invoke the tool - this will handle response_format="content_and_artifact"
            # internally via BaseTool.run() which creates a ToolMessage with artifact
            response = self.tools_by_name[call["name"]].invoke(input_dict, config)

        # GraphInterrupt is a special exception that must always be raised
        except GraphBubbleUp as e:
            raise e
        except Exception as e:
            # Handle errors according to configuration
            if isinstance(self.handle_tool_errors, tuple):
                handled_types = self.handle_tool_errors
            elif callable(self.handle_tool_errors):
                handled_types = _infer_handled_types(self.handle_tool_errors)
            else:
                # Default behavior is catching all exceptions
                handled_types = (Exception,)

            # Re-raise if unhandled
            if not self.handle_tool_errors or not isinstance(e, handled_types):
                raise e

            # Create error message
            content = _handle_tool_error(e, flag=self.handle_tool_errors)
            return ToolMessage(
                content=content,
                name=call["name"],
                tool_call_id=call["id"],
                status="error",
            )

        # Process the response
        if isinstance(response, ToolMessage):
            # Tool returned a ToolMessage (which should have artifact if applicable)
            # Ensure content is properly formatted
            response.content = cast(
                Union[str, list], msg_content_output(response.content)
            )
            # The artifact, if present, is already on the ToolMessage
            return response
        # This shouldn't happen with properly configured LangChain tools
        # but we handle it for robustness
        raise TypeError(
            f"Tool {call['name']} returned unexpected type: {type(response)}. "
            f"Expected ToolMessage but got {response}"
        )

    async def _arun_one(
        self,
        call: ToolCall,
        input_type: Literal["list", "dict", "tool_calls"],
        config: RunnableConfig,
    ) -> ToolMessage:
        """Run a single tool asynchronously, ensuring artifact handling.

        Async version of _run_one that ensures artifacts are properly handled
        for async tool invocations.
        """
        # Validate the tool call first
        if invalid_tool_message := self._validate_tool_call(call):
            return invalid_tool_message

        try:
            # Prepare the input
            input_dict = {**call, **{"type": "tool_call"}}

            # Invoke the tool asynchronously
            tool = self.tools_by_name[call["name"]]
            response = await tool.ainvoke(input_dict, config)

        # GraphInterrupt must always be raised
        except GraphBubbleUp as e:
            raise e
        except Exception as e:
            # Handle errors according to configuration
            if isinstance(self.handle_tool_errors, tuple):
                handled_types = self.handle_tool_errors
            elif callable(self.handle_tool_errors):
                handled_types = _infer_handled_types(self.handle_tool_errors)
            else:
                handled_types = (Exception,)

            # Re-raise if unhandled
            if not self.handle_tool_errors or not isinstance(e, handled_types):
                raise e

            # Create error message
            content = _handle_tool_error(e, flag=self.handle_tool_errors)
            return ToolMessage(
                content=content,
                name=call["name"],
                tool_call_id=call["id"],
                status="error",
            )

        # Process the response
        if isinstance(response, ToolMessage):
            # Tool returned a ToolMessage with potential artifact
            response.content = cast(
                Union[str, list], msg_content_output(response.content)
            )
            return response
        # Unexpected response type
        raise TypeError(
            f"Tool {call['name']} returned unexpected type: {type(response)}. "
            f"Expected ToolMessage but got {response}"
        )
