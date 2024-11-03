from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from neuron_server.database import database
from typing import Self, Optional, List
from neuron_server.models.class_factory import create_model


class PersonalityModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(description="How the personality is referred to in the chat")
    context: str = Field(
        description="Information supplied by the personality for additional context"
    )
    memory: str = Field(
        description="Information about the personality's preferences and history"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    def get_context_prompt(self) -> str:
        return f"""\
You the assistant are called {self.name}. Use the following custom instructions to guide your responses:
\"\"\"
{self.context}
\"\"\"""".strip()

    def get_memory_prompt(self) -> str:
        if not self.memory or len(self.memory.strip()) == 0:
            return ""
        return f"""\
Based on past conversations you have determined the following about the personality:
\"\"\"
{self.memory}
\"\"\"""".strip()

    @classmethod
    def create_table_if_not_exists(cls):
        cursor = database.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS personalities (
                id TEXT PRIMARY KEY,
                name TEXT,
                context TEXT DEFAULT '',
                memory TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        database.commit()

    @classmethod
    def create(
        cls, name: str, context: str, memory: str, id: Optional[UUID] = None
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "INSERT INTO personalities (id, name, context, memory) VALUES (?, ?, ?, ?) RETURNING *",
            (str(id) if id else str(uuid4()), name, context, memory),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Personality not created")
        record = create_model(cls, data)
        database.commit()
        return record

    @classmethod
    def delete(cls, id: UUID):
        cursor = database.cursor()
        cursor.execute("DELETE FROM personalities WHERE id = ?", (str(id),))
        database.commit()

    @classmethod
    def update(cls, id: UUID, name: str, context: str, memory: str) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "UPDATE personalities SET name = ?, context = ?, memory = ? WHERE id = ? RETURNING *",
            (name, context, memory, str(id)),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Personality not updated")
        record = create_model(cls, data)
        database.commit()
        return record

    @classmethod
    def list(cls) -> List[Self]:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM personalities")
        data = cursor.fetchall()
        return [create_model(cls, row) for row in data]

    @classmethod
    def get(cls, id: UUID) -> Self:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM personalities WHERE id = ?", (str(id),))
        data = cursor.fetchone()
        return create_model(cls, data) if data else None

    def save(self):
        cursor = database.cursor()
        cursor.execute(
            "UPDATE personalities SET name = ?, context = ?, memory = ?, updated_at = ? WHERE id = ?",
            (self.name, self.context, self.memory, datetime.now(), str(self.id)),
        )
        database.commit()
