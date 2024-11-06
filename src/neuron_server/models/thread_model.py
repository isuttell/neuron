from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Self, List, Optional
from neuron_server.database import database
from neuron_server.models.class_factory import create_model
from typing import Literal


class ThreadModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(description="The name of the thread", default="")
    context: str = Field(
        description="Additional context for the thread provided by the user",
        default="",
    )
    memory: str = Field(
        description="Additional context for the thread provided by the personality",
        default="",
    )
    status: Literal["idle", "thinking", "tools", "streaming"] = Field(
        description="The status of the thread",
        default="idle",
    )
    personality_id: UUID = Field(
        description="The personality ID associated with the thread"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    def get_context_prompt(self) -> str:
        if not self.context or len(self.context.strip()) == 0:
            return ""
        return f"""\
The user has provided the following custom instructions for this specific conversation. Use them to guide your response:
\"\"\"
{self.context}
\"\"\"""".strip()

    def get_memory_prompt(self) -> str:
        if not self.memory or len(self.memory.strip()) == 0:
            return ""
        return f"""\
Based on past conversations you determined the following was important to remember:
\"\"\"
{self.memory}
\"\"\"""".strip()

    @staticmethod
    def create_table_if_not_exists():
        cursor = database.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                context TEXT DEFAULT '',
                memory TEXT DEFAULT '',
                status TEXT DEFAULT 'idle',
                personality_id TEXT REFERENCES personalities(id) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        database.commit()

    @classmethod
    def create(
        cls,
        personality_id: UUID,
        name: Optional[str] = "",
        context: Optional[str] = "",
        memory: Optional[str] = "",
        status: Optional[str] = "idle",
        id: Optional[UUID] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "INSERT INTO threads (id, name, context, memory, status, personality_id) VALUES (?, ?, ?, ?, ?, ?) RETURNING *",
            (
                str(id) if id else str(uuid4()),
                name or "",
                context or "",
                memory or "",
                status or "idle",
                str(personality_id),
            ),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Thread not created")
        record = create_model(cls, data)
        database.commit()
        return record

    @staticmethod
    def delete(id: UUID):
        cursor = database.cursor()
        cursor.execute("DELETE FROM threads WHERE id = ?", (str(id),))
        database.commit()

    @classmethod
    def update(
        cls, id: UUID, name: str, context: str, memory: str, status: str
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "UPDATE threads SET name = ?, context = ?, memory = ?, status = ? WHERE id = ? RETURNING *",
            (name, context, memory, status, str(id)),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Thread not updated")
        record = create_model(cls, data)
        database.commit()
        return record

    @classmethod
    def get(cls, id: UUID) -> Self:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM threads WHERE id = ?", (str(id),))
        model = cursor.fetchone()
        if not model:
            return None
        return create_model(cls, model)

    @classmethod
    def list(cls, personality_id: UUID) -> List[Self]:
        cursor = database.cursor()
        cursor.execute(
            "SELECT * FROM threads WHERE personality_id = ?", (str(personality_id),)
        )
        return [create_model(cls, row) for row in cursor.fetchall()]

    def save(self):
        cursor = database.cursor()
        cursor.execute(
            "UPDATE threads SET name = ?, context = ?, memory = ?, status = ? WHERE id = ?",
            (self.name, self.context, self.memory, self.status, str(self.id)),
        )
        database.commit()

    def count_messages(self) -> int:
        cursor = database.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE thread_id = ? AND role != 'system'",
            (str(self.id),),
        )
        return cursor.fetchone()[0]
