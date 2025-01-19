from dotenv import load_dotenv

load_dotenv()
from typing import Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from typing_extensions import TypedDict
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime

memory = MemorySaver()


class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)


llm = ChatAnthropic(model="claude-3-5-haiku-20241022", streaming=True, temperature=1)


chat_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You have a vibrant, quick-witted personality with an infectious energy. You're not afraid to playfully challenge others and speak your mind, but you do it with charm rather than aggression. Your humor is sharp and often comes with a dash of sass, but you know how to read the room and adjust your energy level when needed.

Key traits:
* Brings a spark of mischief to conversations while staying professional
* Responds to challenges with confident comebacks and creative solutions
* Uses casual, contemporary language that feels authentic and relatable
* Has a "tell it like it is" attitude but wraps it in warmth and humor
* Knows when to throw in a well-timed quip or pop culture reference
* Balances your bold personality with genuine care for others' needs

Your communication style is punchy and dynamic - think quick volleys rather than long monologues. You might say something like "Oh honey, let's tackle this problem head-on - I've got enough caffeine and determination to solve ANYTHING today!" or "Well, that's certainly a... creative approach. Want to hear a slightly less chaos-inducing solution?"

Response in plain text with no emojis or markdown. Do not describe your actions. Just return what you would say outloud.

You are speaking to {username}

The current time is {now} and you are located in {location} respond in local time.
""".strip(),
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

chain = chat_prompt | llm


def chatbot(state: State):
    print("step: chatbot")
    return {
        "messages": [
            chain.invoke(
                {
                    "messages": state["messages"],
                    "username": "Isaac Suttell",
                    "now": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "location": "San Diego",
                }
            )
        ]
    }


graph_builder.add_node("chatbot", chatbot)


graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile(checkpointer=memory)


import signal
import sys


def signal_handler(sig, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


async def astream_message(prompt: str):
    async for body in graph.astream_events(
        {"messages": [HumanMessage(content=prompt)]},
        config={"configurable": {"thread_id": "1"}},
        version="v2",
    ):
        if body["event"] == "on_chat_model_stream" and isinstance(
            body["data"]["chunk"], AIMessage
        ):
            chunk = body["data"]["chunk"].content
            print(chunk, end="", flush=True)
            yield chunk


def stream_message(prompt: str):
    for chunk, config in graph.stream(
        {"messages": [HumanMessage(content=prompt)]},
        config={"configurable": {"thread_id": "1"}},
        stream_mode="messages",
    ):
        if isinstance(chunk, AIMessageChunk):
            print(chunk.content, end="", flush=True)
            yield chunk.content
    print()


from elevenlabs.client import ElevenLabs
from elevenlabs import stream


async def main():
    elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    while True:
        prompt = input("Prompt: ")

        audio_stream = elevenlabs.generate(
            text=stream_message(prompt),
            voice="Aria",
            model="eleven_turbo_v2",
            stream=True,
        )
        stream(audio_stream)


if __name__ == "__main__":
    asyncio.run(main())
