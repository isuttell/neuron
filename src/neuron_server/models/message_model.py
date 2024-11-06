from pydantic import BaseModel, Field, field_validator
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Literal, Self, Optional, List
from neuron_server.database import database
from neuron_server.models.class_factory import create_model
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.messages.tool import (
    ToolCall,
)
import json
from typing import Dict, Any, Tuple, Optional
from typing_extensions import TypedDict

Role = Literal["human", "ai", "system", "tool"]


class UsageMetadata(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_token_details: Dict[str, Any]


class MessageModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
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
    def create_table_if_not_exists(cls):
        cursor = database.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                thread_id uuid REFERENCES threads(id) NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL,
                tool_call_id TEXT,
                tool_calls TEXT NOT NULL DEFAULT '[]',
                usage_metadata TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        database.commit()

    @classmethod
    def set(cls, id: str, key: str, value: Any) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "UPDATE messages SET ? = ?, updated_at = ? WHERE id = ? RETURNING *",
            (key, value, datetime.now(timezone.utc).astimezone().isoformat(), str(id)),
        )
        database.commit()
        return create_model(cls, cursor.fetchone())

    @classmethod
    def create(
        cls,
        role: Role,
        thread_id: UUID,
        content: str = "",
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        usage_metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "INSERT INTO messages (id, thread_id, content, role, tool_call_id, tool_calls, usage_metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING *",
            (
                str(id) if id else str(uuid4()),
                str(thread_id),
                content,
                role,
                tool_call_id,
                json.dumps(tool_calls or []),
                json.dumps(usage_metadata or {}),
                datetime.now(timezone.utc).astimezone().isoformat(),
                datetime.now(timezone.utc).astimezone().isoformat(),
            ),
        )
        data = cursor.fetchone()
        record = create_model(cls, data)
        database.commit()
        return record

    @classmethod
    def upsert(
        cls,
        content: str,
        role: Role,
        thread_id: UUID,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        usage_metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute("SELECT tool_calls FROM messages WHERE id = ?", (str(id),))
        existing_tool_calls = cursor.fetchone()
        existing_tool_calls_list = (
            json.loads(existing_tool_calls[0]) if existing_tool_calls else []
        )

        # Merge existing tool calls with new ones, avoiding duplicates
        merged_tool_calls = list(
            {
                tool_call["id"]: tool_call
                for tool_call in existing_tool_calls_list + (tool_calls or [])
            }.values()
        )

        cursor.execute(
            "INSERT INTO messages (id, thread_id, content, role, tool_call_id, tool_calls, usage_metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (id) DO UPDATE SET content = ?, role = ?, tool_call_id = ?, tool_calls = ?, usage_metadata = ?, updated_at = ? RETURNING *",
            (
                str(id) if id else str(uuid4()),
                str(thread_id),
                content,
                role,
                tool_call_id,
                json.dumps(merged_tool_calls),
                json.dumps(usage_metadata or {}),
                created_at or datetime.now(timezone.utc).astimezone().isoformat(),
                datetime.now(timezone.utc).astimezone().isoformat(),
                content,
                role,
                tool_call_id,
                json.dumps(merged_tool_calls),
                json.dumps(usage_metadata or {}),
                datetime.now(timezone.utc).astimezone().isoformat(),
            ),
        )
        data = cursor.fetchone()
        record = create_model(cls, data)
        database.commit()
        return record

    @classmethod
    def append_content(cls, id: str, chunk: str, role: str, thread_id: UUID) -> Self:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (str(id),))
        record = cursor.fetchone()
        if record:
            message: Self = create_model(cls, record)
            cursor.execute(
                "UPDATE messages SET content = ?, updated_at = ? WHERE id = ? RETURNING *",
                (
                    message.content + chunk,
                    datetime.now(timezone.utc).astimezone().isoformat(),
                    str(id),
                ),
            )
        else:
            cursor.execute(
                "INSERT INTO messages (id, thread_id, content, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) RETURNING *",
                (
                    str(id) if id else str(uuid4()),
                    str(thread_id),
                    chunk,
                    role,
                    datetime.now(timezone.utc).astimezone().isoformat(),
                    datetime.now(timezone.utc).astimezone().isoformat(),
                ),
            )
        return create_model(cls, cursor.fetchone())

    @classmethod
    def count_tokens(cls) -> Tuple[int, int]:
        cursor = database.cursor()
        cursor.execute("SELECT count(id) FROM messages")
        count = cursor.fetchone()[0]
        offset = 0
        input_tokens = 0
        output_tokens = 0
        while offset < count:
            cursor.execute(
                "SELECT usage_metadata FROM messages ORDER BY created_at ASC LIMIT ? OFFSET ?",
                (100, offset),
            )
            rows = cursor.fetchall()
            offset += len(rows)
            for row in rows:
                usage_metadata: UsageMetadata = json.loads(row[0])
                assert isinstance(usage_metadata, dict)
                if isinstance(usage_metadata.get("input_tokens"), int):
                    input_tokens += usage_metadata["input_tokens"]
                if isinstance(usage_metadata.get("output_tokens"), int):
                    output_tokens += usage_metadata["output_tokens"]
        return input_tokens, output_tokens

    @classmethod
    def list(cls, thread_id: UUID) -> List[Self]:
        cursor = database.cursor()
        cursor.execute(
            "SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at ASC",
            (str(thread_id),),
        )
        records = cursor.fetchall()
        return [create_model(cls, row) for row in records]

    @classmethod
    def count(cls, thread_id: UUID) -> int:
        cursor = database.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE thread_id = ?", (str(thread_id),)
        )
        return cursor.fetchone()[0]

    @classmethod
    def delete(cls, id: str):
        cursor = database.cursor()
        cursor.execute("DELETE FROM messages WHERE id = ?", (str(id),))
        database.commit()

    @classmethod
    def get(cls, id: str) -> Self:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (str(id),))
        return create_model(cls, cursor.fetchone())

    @classmethod
    def update(
        cls,
        id: str,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        usage_metadata: Optional[Dict[str, Any]] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "UPDATE messages SET content = ?, tool_call_id = ?, tool_calls = ?, usage_metadata = ?, updated_at = ? WHERE id = ? RETURNING *",
            (
                content,
                tool_call_id,
                json.dumps(tool_calls or []),
                json.dumps(usage_metadata or {}),
                datetime.now(timezone.utc).astimezone().isoformat(),
                str(id),
            ),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Message not found")
        record = create_model(cls, data)
        database.commit()
        return record

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
                raise ValueError("Tool call ID is required for tool messages")
            return ToolMessage(content=self.content, tool_call_id=self.tool_call_id)
        else:
            raise ValueError(f"Invalid role: {self.role}")
