from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import Literal, Self, Optional, List
from neuron_server.database import database
from neuron_server.models.class_factory import create_model
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    AIMessage,
    HumanMessage,
    FunctionMessage,
    ToolMessage,
)
from typing import Type

Role = Literal["human", "ai", "system", "tool", "function"]


class MessageModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: UUID = Field(description="The ID of the thread the message belongs to")
    content: str = Field(..., description="The content of the message")
    role: Role = Field(description="The role of the message sender")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        database.commit()

    @classmethod
    def create(
        cls,
        content: str,
        role: Role,
        thread_id: UUID,
        id: Optional[str] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "INSERT INTO messages (id, thread_id, content, role) VALUES (?, ?, ?, ?) RETURNING *",
            (
                str(id) if id else str(uuid4()),
                str(thread_id),
                content,
                role,
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
        id: Optional[str] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "INSERT INTO messages (id, thread_id, content, role) VALUES (?, ?, ?, ?) ON CONFLICT (id) DO UPDATE SET content = ?, role = ? RETURNING *",
            (
                str(id) if id else str(uuid4()),
                str(thread_id),
                content,
                role,
                content,
                role,
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
                "UPDATE messages SET content = ? WHERE id = ? RETURNING *",
                (message.content + chunk, str(id)),
            )
        else:
            cursor.execute(
                "INSERT INTO messages (id, thread_id, content, role) VALUES (?, ?, ?, ?) RETURNING *",
                (
                    str(id) if id else str(uuid4()),
                    str(thread_id),
                    chunk,
                    role,
                ),
            )
        return create_model(cls, cursor.fetchone())

    @classmethod
    def list(cls, thread_id: UUID) -> List[Self]:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM messages WHERE thread_id = ?", (str(thread_id),))
        return [create_model(cls, row) for row in cursor.fetchall()]

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
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "UPDATE messages SET content = ? WHERE id = ? RETURNING *",
            (content, str(id)),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Message not found")
        record = create_model(cls, data)
        database.commit()
        return record

    def to_message(self) -> BaseMessage:
        model: Type[BaseMessage]
        if self.role == "human":
            model = HumanMessage
        elif self.role == "ai":
            model = AIMessage
        elif self.role == "system":
            model = SystemMessage
        elif self.role == "tool":
            model = ToolMessage
        elif self.role == "function":
            model = FunctionMessage
        else:
            raise ValueError(f"Invalid role: {self.role}")

        return model(
            content=self.content,
        )
