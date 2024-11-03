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
    ThreadExtended,
)
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from datetime import datetime
from typing import List
import re
from neuron_server.llms.llm import LLM
from uuid import UUID
from neuron_server.llms.providers import get_provider
from neuron_server.llms.clean_eos_tokens import clean_eos_tokens


async def update_thread_status(thread: ThreadModel, status: str):
    if thread.status != status:
        logger.debug(f"Updating thread {thread.id} status to {status}")
        thread.status = status
        thread.save()
        await websocket.send(
            GetThreadResponse(
                thread=ThreadExtended(
                    **thread.model_dump(), message_count=thread.count_messages()
                )
            ).model_dump_json()
        )


async def stream_messages(
    provider: LLM, messages: List[BaseMessage], thread: ThreadModel
):
    async for body in provider.executor.astream(
        {
            "messages": messages,
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "run_name": "chat",
            "metadata": {"thread_id": thread.id},
        },
        stream_mode="messages",
    ):
        messages.append(body)
        content = (
            clean_eos_tokens(body.content).strip()
            if isinstance(body.content, str)
            else ""
        )
        if isinstance(body, AIMessage) and len(content) > 0:
            message = MessageModel.upsert(
                id=body.id, content=content, role="ai", thread_id=thread.id
            )
            await websocket.send(MessageEvent(message=message).model_dump_json())
    return messages


def get_message_content(message: BaseMessage):
    if not message.content:
        return None
    if isinstance(message.content, list):
        return clean_eos_tokens(
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
    return clean_eos_tokens(message.content)


async def astream_events(
    provider: LLM, messages: List[BaseMessage], thread: ThreadModel
):
    index = -1
    async for body in provider.executor.astream_events(
        {
            "messages": messages,
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "run_name": "chat",
            "metadata": {
                "thread_id": thread.id,
            },
        },
        version="v1",
    ):
        kind = body["event"]
        if kind == "on_chat_model_stream":
            content: str | None = None
            if isinstance(body["data"]["chunk"], str):
                content = clean_eos_tokens(body["data"]["chunk"])
            elif isinstance(body["data"]["chunk"], AIMessage):
                output: AIMessage = body["data"]["chunk"]
                content = get_message_content(output)

            if isinstance(content, str) and len(content) > 0:
                content = (
                    content.replace("</thinking>", "```").replace(
                        "<thinking>", "```thinking\n"
                    )
                    if content
                    else None
                )
                await update_thread_status(thread, "streaming")
                MessageModel.append_content(
                    id=body["run_id"], chunk=content, role="ai", thread_id=thread.id
                )
                index += 1
                await websocket.send(
                    PartialMessageEvent(
                        message=PartialMessage(
                            id=body["run_id"],
                            role="ai",
                            content=content,
                            thread_id=thread.id,
                            index=index,
                            status="streaming",
                        )
                    ).model_dump_json()
                )
        elif kind == "on_tool_start":
            await update_thread_status(thread, "tools")
            logger.debug(
                f"Starting tool: {body['name']} with inputs: {body['data'].get('input')}"
            )
        elif kind == "on_tool_end":
            logger.debug(f"Done tool: {body['name']}")
            output = body["data"].get("output")
            if output and isinstance(output, ToolMessage):
                messages.append(output)
        elif kind == "on_chat_model_end":
            output = body["data"]["output"]["generations"][0][0]["message"]
            if output:
                messages.append(output)

            if output and isinstance(output, AIMessage):
                content = get_message_content(output)
                content = (
                    content.replace("</thinking>", "```").replace(
                        "<thinking>", "```thinking\n"
                    )
                    if content
                    else None
                )
                if content and len(content.strip()) > 0:
                    final = MessageModel.upsert(
                        id=body["run_id"],
                        role="ai",
                        content=content,
                        thread_id=thread.id,
                    )
                    await websocket.send(MessageEvent(message=final).model_dump_json())
    return messages


def get_trimmed_messages(
    thread: ThreadModel,
    llm: LLM,
    system_prompts: List[str] = [],
    messages: List[BaseMessage] = [],
) -> List[BaseMessage]:
    records: List[MessageModel] = MessageModel.list(thread.id)
    messages: List[BaseMessage] = [
        SystemMessage(content="\n\n".join(system_prompts)),
        *[record.to_message() for record in records],
        *messages,
    ]
    return llm.message_trimmer.invoke(
        messages, {"run_name": "trim", "metadata": {"thread_id": thread.id}}
    )


async def ainvoke(
    thread_id: UUID,
    prompt: str,
    personality_id: UUID | None = None,
    provider_id: UUID | None = None,
    save_user_message: bool = True,
):
    thread = ThreadModel.get(thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    try:
        await update_thread_status(thread, "thinking")

        personality = PersonalityModel.get(personality_id) if personality_id else None

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
            user_message: MessageModel = MessageModel.create(
                thread_id=thread.id,
                role="human",
                content=prompt,
            )
            # Don't need to wait for this to send
            await websocket.send(
                MessageEvent(
                    message=user_message,
                ).model_dump_json()
            )

        messages = get_trimmed_messages(
            thread=thread,
            llm=provider,
            system_prompts=system_prompts,
            # Only add the user message if we're not saving it as get trimmed pulls from the db
            # so we need to add it here if it's not saved
            messages=[HumanMessage(content=prompt)] if not save_user_message else [],
        )

        if provider.provider == "huggingface":
            await stream_messages(provider, messages, thread)
        else:
            await astream_events(provider, messages, thread)

        await update_thread_status(thread, "thinking")
        # Update the trimmed messages to include the new messages but exclude
        # the tools calls
        messages = get_trimmed_messages(
            thread=thread, llm=provider, system_prompts=system_prompts
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
            thread.save()

        await websocket.send(
            GetThreadResponse(
                thread=ThreadExtended(
                    **thread.model_dump(), message_count=thread.count_messages()
                )
            ).model_dump_json()
        )
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
            thread.save()
            logger.debug(f"Updated memory for thread {thread.id}: \n{thread.memory}")
    finally:
        await update_thread_status(thread, "idle")
