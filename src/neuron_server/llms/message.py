from quart import websocket
from neuron_server.event_router import ErrorEvent
from neuron_server.models import ThreadModel, MessageModel, PersonalityModel
from neuron_server.logger import logger
from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessageEvent,
    PartialMessage,
)
from neuron_server.controllers.events.thread_events import (
    GetThreadResponse,
)
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import re
from neuron_server.llms.llm import LLM
from uuid import UUID
from neuron_server.llms.providers import get_provider
from neuron_server.llms.clean_eos_tokens import clean_eos_tokens
from langchain_core.messages.tool import ToolCall
import json


async def update_thread_status(thread: ThreadModel, status: str):
    if thread.status != status:
        logger.debug(f"Updating thread {thread.id} status to {status}")
        thread.status = status
        await thread.save()
        thread.message_count = await thread.count_messages()
        await websocket.send(GetThreadResponse(thread=thread).model_dump_json())


def get_message_content(message: BaseMessage):
    """Extract the content from a message and format it for display"""
    if not message.content:
        return None
    content: str
    if isinstance(message.content, list):
        content = clean_eos_tokens(
            "\n".join(
                [
                    (
                        c["text"]
                        if isinstance(c, dict) and "text" in c
                        else c if isinstance(c, str) else ""
                    )
                    for c in message.content
                ]
            )
        )
    else:
        content = clean_eos_tokens(message.content)

    return content.replace("</thinking>", "```").replace("<thinking>", "```thinking\n")


async def astream_events(
    provider: LLM, messages: List[BaseMessage], thread: ThreadModel
):
    index = -1
    start_times: Dict[str, datetime] = {}
    async for body in provider.executor.astream_events(
        {
            "messages": messages,
            "now": datetime.now(timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "run_name": "chat",
            "metadata": {
                "thread_id": thread.id,
            },
        },
        version="v2",
    ):
        kind: str = body["event"]
        run_id: str = body["run_id"]
        if run_id not in start_times:
            start_times[run_id] = datetime.now(timezone.utc).astimezone()
        if kind == "on_chat_model_stream":
            chunk = body["data"]["chunk"]
            if isinstance(chunk, AIMessage):
                content = get_message_content(chunk)
                if isinstance(content, str) and len(content) > 0:
                    await update_thread_status(thread, "streaming")
                    index += 1
                    await websocket.send(
                        PartialMessageEvent(
                            message=PartialMessage(
                                id=run_id,
                                role="ai",
                                content=content,
                                thread_id=thread.id,
                                index=index,
                                status="streaming",
                                # Use a stable start time and don't create a new one per event
                                created_at=start_times[run_id],
                            )
                        ).model_dump_json()
                    )

        elif kind == "on_chat_model_end":
            output: AIMessage = body["data"]["output"]
            assert isinstance(output, AIMessage)
            messages.append(output)
            content = get_message_content(output) or ""
            record = await MessageModel.upsert(
                id=output.id.replace("run-", ""),
                content=content,
                role="ai",
                thread_id=thread.id,
                tool_calls=output.tool_calls,
                usage_metadata=output.usage_metadata,
                created_at=start_times[run_id],
            )
            if len(content) > 0:
                await websocket.send(MessageEvent(message=record).model_dump_json())
            await update_thread_status(thread, "thinking")
        elif kind == "on_tool_start":
            await update_thread_status(thread, "tools")
            logger.debug(
                f"Starting tool: {body['name']} with inputs: {body['data'].get('input')}"
            )
        elif kind == "on_tool_end":
            output: ToolMessage = body["data"]["output"]
            assert isinstance(output, ToolMessage)
            preceding_ai_message = next(
                (msg for msg in reversed(messages) if isinstance(msg, AIMessage)),
            )
            # Add a tiny bit of time to the created at so it's more highly likely
            # to be after the preceding AI message which is required for the API
            created_at = start_times[
                preceding_ai_message.id.replace("run-", "")
            ] + timedelta(milliseconds=1)
            messages.append(output)
            record = await MessageModel.upsert(
                id=run_id,
                content=(get_message_content(output) or ""),
                role="tool",
                thread_id=thread.id,
                tool_call_id=output.tool_call_id,
                created_at=created_at,
            )
            await websocket.send(MessageEvent(message=record).model_dump_json())
    return messages


async def get_trimmed_messages(
    thread: ThreadModel,
    llm: LLM,
    system_prompts: List[str] = [],
    messages: List[BaseMessage] = [],
    remove_tools: bool = False,
) -> List[BaseMessage]:
    records: List[MessageModel] = await MessageModel.list(thread.id)
    messages: List[BaseMessage] = [
        SystemMessage(content="\n\n".join(system_prompts)),
        *[record.to_message() for record in records],
        *messages,
    ]
    # Remove tools if we don't care about running them for things like summaries
    if remove_tools:
        messages = [
            message for message in messages if not isinstance(message, ToolMessage)
        ]
        for message in messages:
            if isinstance(message, AIMessage):
                message.tool_calls = []
    return await llm.message_trimmer.ainvoke(
        messages, {"run_name": "trim", "metadata": {"thread_id": thread.id}}
    )


async def ainvoke(
    thread_id: UUID,
    prompt: str,
    personality_id: UUID | None = None,
    provider_id: UUID | None = None,
    save_user_message: bool = True,
    update_memory: bool = False,
):
    thread = await ThreadModel.get(thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    try:
        await update_thread_status(thread, "thinking")

        personality = (
            await PersonalityModel.get(personality_id) if personality_id else None
        )

        system_prompts = [
            prompt
            for prompt in [
                personality.get_context_prompt(),
                thread.get_context_prompt(),
                thread.get_memory_prompt(),
            ]
            if prompt
        ]

        provider = get_provider(provider_id)

        if save_user_message:
            user_message: MessageModel = await MessageModel.create(
                thread_id=thread.id,
                role="human",
                content=prompt,
            )
            logger.debug(
                f"Sending user message {user_message.id} at {user_message.created_at.isoformat()}"
            )
            # Don't need to wait for this to send
            await websocket.send(
                MessageEvent(
                    message=user_message,
                ).model_dump_json()
            )

        messages = await get_trimmed_messages(
            thread=thread,
            llm=provider,
            system_prompts=system_prompts,
            # Only add the user message if we're not saving it as get trimmed pulls from the db
            # so we need to add it here if it's not saved
            messages=[HumanMessage(content=prompt)] if not save_user_message else [],
        )
        initial_messages_length = len(messages)
        messages = await astream_events(provider, messages, thread)
        new_messages = messages[initial_messages_length:]

        # Add the tool calls to the preceding AI message
        updated_messages: List[AIMessage] = []
        for message in new_messages:
            if isinstance(message, ToolMessage):
                # Find the preceding AI message
                preceding_ai_message = next(
                    (
                        msg
                        for msg in reversed(new_messages[: new_messages.index(message)])
                        if isinstance(msg, AIMessage)
                    ),
                    None,
                )
                if not preceding_ai_message:
                    raise ValueError("No preceding AI message found")

                tool_call: ToolCall = {
                    "id": message.tool_call_id,
                    "name": message.name,
                    "args": {},
                }
                if tool_call["id"] not in (
                    tc["id"] for tc in preceding_ai_message.tool_calls
                ):
                    updated_messages.append(preceding_ai_message)
                    preceding_ai_message.tool_calls.append(tool_call)

        # Ensure the tool calls are saved in the db correctly
        for message in updated_messages:
            await MessageModel.set(
                id=message.id.replace("run-", ""),
                key="tool_calls",
                value=json.dumps(message.tool_calls),
            )

        await update_thread_status(thread, "thinking")
        # Update the trimmed messages to include the new messages but exclude
        # the tools calls
        messages = await get_trimmed_messages(
            thread=thread,
            llm=provider,
            system_prompts=system_prompts,
            remove_tools=True,
        )

        summary_response = await provider.title.ainvoke(
            {
                "messages": [
                    *messages,
                    HumanMessage(
                        content="Please update the title of our conversation so I can easily find it later"
                    ),
                ],
                "last_title": thread.name or "No title yet",
            },
            {"run_name": "title", "metadata": {"thread_id": thread.id}},
        )
        summary = get_message_content(summary_response)
        if isinstance(summary, str) and len(summary.strip()) > 0:
            thread.name = re.sub(
                r'^([`*"]){0,3}|([`*"]){0,3}$',
                "",
                clean_eos_tokens(summary),
            )
            await thread.save()

        thread.message_count = await thread.count_messages()
        await websocket.send(GetThreadResponse(thread=thread).model_dump_json())

        if update_memory:
            memory_response = await provider.memory.ainvoke(
                {
                    "messages": [
                        *messages,
                        *(
                            [
                                HumanMessage(
                                    content="Please update the memory of our conversation"
                                )
                            ]
                            if provider.provider != "openai"
                            else []
                        ),
                    ],
                    "memory": thread.memory or "No memory yet",
                },
                {"run_name": "memory", "metadata": {"thread_id": thread.id}},
            )
            memory = get_message_content(memory_response)
            if isinstance(memory, str) and len(memory.strip()) > 0:
                thread.memory = memory
                await thread.save()
                logger.debug(
                    f"Updated memory for thread {thread.id}: \n{thread.memory}"
                )
    finally:
        await update_thread_status(thread, "idle")
