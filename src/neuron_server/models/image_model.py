from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Self, List, Optional
from neuron_server.database import database
from neuron_server.models.class_factory import create_model


class ImageModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    image: Optional[str] = Field(
        description="Either a base64 encoded image or a filename", default=None
    )
    prompt: str = Field(description="The prompt used to generate the image")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    @staticmethod
    def create_table_if_not_exists():
        cursor = database.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                image TEXT,
                prompt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        database.commit()

    @classmethod
    def create(
        cls,
        prompt: str,
        image: Optional[str] = None,
        id: Optional[UUID] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "INSERT INTO images (id, image, prompt) VALUES (?, ?, ?) RETURNING *",
            (
                str(id) if id else str(uuid4()),
                image,
                prompt,
            ),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Image not created")
        record = create_model(cls, data)
        database.commit()
        return record

    @staticmethod
    def delete(id: UUID):
        cursor = database.cursor()
        cursor.execute("DELETE FROM images WHERE id = ?", (str(id),))
        database.commit()

    @classmethod
    def update(
        cls,
        id: UUID,
        prompt: str,
        image: Optional[str] = None,
    ) -> Self:
        cursor = database.cursor()
        cursor.execute(
            "UPDATE images SET image = ?, prompt = ? WHERE id = ? RETURNING *",
            (image, prompt, str(id)),
        )
        data = cursor.fetchone()
        if not data:
            raise ValueError("Image not updated")
        record = create_model(cls, data)
        database.commit()
        return record

    def update_image(self, image: Optional[str] = None) -> Self:
        return self.update(self.id, image, self.prompt)

    @classmethod
    def get(cls, id: UUID) -> Self:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", (str(id),))
        model = cursor.fetchone()
        if not model:
            return None
        return create_model(cls, model)

    @classmethod
    def list(cls) -> List[Self]:
        cursor = database.cursor()
        cursor.execute("SELECT * FROM images ORDER BY created_at DESC")
        return [create_model(cls, row) for row in cursor.fetchall()]

    def save(self):
        cursor = database.cursor()
        cursor.execute(
            "UPDATE images SET image = ?, prompt = ? WHERE id = ?",
            (self.image, self.prompt, str(self.id)),
        )
        database.commit()
