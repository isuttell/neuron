from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Literal, Optional, List, Dict, Any, Tuple, Self
from sqlalchemy import select, delete, func
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.messages.tool import ToolCall
from neuron_server.database import get_session, Message
from sqlalchemy.dialects.postgresql import insert as pg_insert
import json
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, field_validator

Role = Literal["human", "ai", "system", "tool"]


class UsageMetadata(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_token_details: Dict[str, Any]


class MessageModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    thread_id: UUID = Field(description="The ID of the thread the message belongs to")
    content: str = Field(description="The content of the message")
    role: Role = Field(description="The role of the message sender")
    tool_call_id: Optional[str] = Field(
        default=None, description="The ID of the tool call the message belongs to"
    )
    tool_calls: List[ToolCall] = Field(
        default=[], description="The tool calls the message belongs to"
    )
    usage_metadata: Dict[str, Any] = Field(
        default={}, description="The usage metadata of the message"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    @field_validator("tool_calls", mode="before")
    def parse_tool_calls(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for tool_calls: {e}")
        return value

    @field_validator("usage_metadata", mode="before")
    def parse_usage_metadata(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for usage_metadata: {e}")
        return value

    @classmethod
    async def set(cls, id: UUID, key: str, value: Any) -> Self:
        async with get_session() as session:
            message = await session.get(Message, id)
            if not message:
                raise ValueError("Message not found")
            setattr(message, key, value)
            session.add(message)
            await session.commit()
            return cls(**message.__dict__)

    @classmethod
    async def create(
        cls,
        role: Role,
        thread_id: UUID,
        content: str = "",
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        usage_metadata: Optional[Dict[str, Any]] = None,
        id: Optional[UUID] = None,
    ) -> Self:
        async with get_session() as session:
            new_message = Message(
                id=id,
                thread_id=thread_id,
                content=content,
                role=role,
                tool_call_id=tool_call_id,
                tool_calls=json.dumps(tool_calls or []),
                usage_metadata=json.dumps(usage_metadata or {}),
            )
            session.add(new_message)
            await session.commit()
            return cls(**new_message.__dict__)

    @classmethod
    async def upsert(
        cls,
        content: str,
        role: Role,
        thread_id: UUID,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        usage_metadata: Optional[Dict[str, Any]] = None,
        id: Optional[UUID] = None,
        created_at: Optional[str] = None,
    ) -> Self:
        async with get_session() as session:
            stmt = (
                pg_insert(Message)
                .values(
                    id=id,
                    thread_id=thread_id,
                    content=content,
                    role=role,
                    tool_call_id=tool_call_id,
                    tool_calls=json.dumps(tool_calls or []),
                    usage_metadata=json.dumps(usage_metadata or {}),
                    created_at=created_at,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "content": content,
                        "role": role,
                        "tool_call_id": tool_call_id,
                        "tool_calls": json.dumps(tool_calls or []),
                        "usage_metadata": json.dumps(usage_metadata or {}),
                    },
                )
                .returning(Message)
            )
            result = await session.execute(stmt)
            await session.commit()
            return cls(**result.scalar_one().__dict__)

    @classmethod
    async def append_content(cls, message: Message, chunk: str) -> Self:
        async with get_session() as session:
            message.content += chunk
            session.add(message)
            await session.commit()
            return cls(**message.__dict__)

    @classmethod
    async def count_tokens(cls) -> Tuple[int, int]:
        async with get_session() as session:
            stmt = select(Message.usage_metadata)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            input_tokens = 0
            output_tokens = 0
            for row in rows:
                usage_metadata: UsageMetadata = json.loads(row)
                if isinstance(usage_metadata.get("input_tokens"), int):
                    input_tokens += usage_metadata["input_tokens"]
                if isinstance(usage_metadata.get("output_tokens"), int):
                    output_tokens += usage_metadata["output_tokens"]
            return input_tokens, output_tokens

    @classmethod
    async def list(cls, thread_id: UUID) -> List[Self]:
        async with get_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at.asc())
            )
            return [cls(**message.__dict__) for message in result.scalars().all()]

    @staticmethod
    async def count(thread_id: UUID) -> int:
        async with get_session() as session:
            async with session.begin():
                stmt = select(func.count(Message.id)).where(
                    Message.thread_id == thread_id
                )
                result = await session.execute(stmt)
                return result.scalar()

    @staticmethod
    async def delete(id: UUID) -> None:
        async with get_session() as session:
            await session.execute(delete(Message).where(Message.id == id))

    @classmethod
    async def get(cls, id: UUID) -> Optional[Self]:
        async with get_session() as session:
            data = await session.get(Message, id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def update(
        cls,
        id: UUID,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        usage_metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        async with get_session() as session:
            message = await session.get(Message, id)
            if not message:
                raise ValueError("Message not found")
            message.content = content
            message.tool_call_id = tool_call_id
            message.tool_calls = json.dumps(tool_calls or [])
            message.usage_metadata = json.dumps(usage_metadata or {})
            session.add(message)
            await session.commit()
            return cls(**message.__dict__)

    def to_message(self) -> BaseMessage:
        if self.role == "human":
            return HumanMessage(
                content=self.content,
            )
        elif self.role == "ai":
            return AIMessage(
                content=self.content,
                tool_calls=self.tool_calls,
            )
        elif self.role == "tool":
            if not self.tool_call_id:
                raise ValueError("Tool call ID is required for tool selfs")
            return ToolMessage(content=self.content, tool_call_id=self.tool_call_id)
        else:
            raise ValueError(f"Invalid role: {self.role}")
