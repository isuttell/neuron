from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from neuron_server.database import database
from typing import Self, Optional
from neuron_server.models.class_factory import create_model


class AgentModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    name: str = Field(description="The name of the agent")
    context: str = Field(
        description="Information supplied by the user for additional context"
    )

    @classmethod
    def create_table_if_not_exists(cls):
        cursor = database.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT,
                context TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        database.commit()

    @classmethod
    def create(cls, name: str, context: str, id: Optional[UUID] = None) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "INSERT INTO agents (id, name, context) VALUES (?, ?, ?) RETURNING *",
            (str(id) if id else str(uuid4()), name, context),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Agent not created")
        record = create_model(cls, data)
        database.commit()
        return record

    @classmethod
    def delete(cls, id: UUID):
        cursor = database.cursor()
        cursor.execute("DELETE FROM agents WHERE id = ?", (id,))
        database.commit()

    @classmethod
    def update(cls, id: UUID, name: str, context: str) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "UPDATE agents SET name = ?, context = ? WHERE id = ? RETURNING *",
            (name, context, str(id)),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Agent not updated")
        record = create_model(cls, data)
        database.commit()
        return record
