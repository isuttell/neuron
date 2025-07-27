import builtins
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select

from neuron_server.database import Personality, PersonalityUser, get_session
from neuron_server.models.personality_user_model import PersonalityUserModel


class PersonalityModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(description="How the personality is referred to in the chat")
    description: str = Field(
        description="A short description of the personality's role and purpose"
    )
    context: str = Field(
        description="Information supplied by the personality for additional context"
    )
    logo: str | None = Field(
        description="A URL to an image that represents the personality", default=None
    )
    memory: str = Field(
        description="Information about the personality's preferences and history"
    )
    tool_set: str | None = Field(
        description="The tool set to use for the personality", default=None
    )
    default: bool = Field(
        description="Whether this is the default personality", default=False
    )
    status: str = Field(
        description="Current status of the personality (empty string means idle)",
        default="",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @classmethod
    def _from_db_record(cls, personality: Personality) -> Self:
        """Create a PersonalityModel from a database record, handling None values.

        Args:
            personality: The database record to convert

        Returns:
            A PersonalityModel instance with proper defaults
        """
        data = personality.__dict__.copy()
        # Handle None status values from database (convert to empty string)
        if data.get("status") is None:
            data["status"] = ""
        return cls(**data)

    @dataclass
    class CreateParams:
        name: str
        description: str
        context: str
        memory: str
        creator_id: str
        logo: str | None = None
        tool_set: str | None = None
        personality_id: UUID | None = None

    @staticmethod
    async def _ensure_single_default() -> None:
        """Ensure only one personality is marked as default."""
        async with get_session() as session:
            # Clear all existing defaults
            stmt = select(Personality).where(Personality.default.is_(True))
            result = await session.execute(stmt)
            personalities = result.scalars().all()
            for personality in personalities:
                personality.default = False
            await session.commit()

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new personality and add the creator as an admin.

        Args:
            params: Parameters for creating the personality

        Returns:
            The created PersonalityModel instance
        """
        async with get_session() as session:
            personality = Personality(
                id=params.personality_id,
                name=params.name,
                description=params.description,
                context=params.context,
                memory=params.memory,
                tool_set=params.tool_set,
                logo=params.logo,
                default=False,  # New personalities are never default
            )
            session.add(personality)
            await session.commit()

            # Add the creator as an admin
            personality_user = PersonalityUser(
                personality_id=personality.id,
                user_id=params.creator_id,
                role="admin",
            )
            session.add(personality_user)
            await session.commit()

            return cls._from_db_record(personality)

    @staticmethod
    async def delete(personality_id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(Personality, personality_id))
            await session.commit()

    @dataclass
    class UpdateParams:
        personality_id: UUID
        name: str
        description: str
        context: str
        memory: str
        logo: str | None
        tool_set: str | None

    @classmethod
    async def update(cls, params: UpdateParams) -> Self:
        async with get_session() as session:
            personality = await session.get(Personality, params.personality_id)
            personality.name = params.name
            personality.description = params.description
            personality.context = params.context
            personality.memory = params.memory
            personality.tool_set = params.tool_set
            personality.logo = params.logo
            # Don't update default field in regular update
            session.add(personality)
            await session.commit()
            return cls._from_db_record(personality)

    @classmethod
    async def set(
        cls,
        personality_id: UUID,
        key: str,
        value: str | int | float | bool | dict | list | None,
    ) -> Self:
        async with get_session() as session:
            # If setting default to True, clear other defaults
            if key == "default" and value is True:
                await cls._ensure_single_default()

            personality = await session.get(Personality, personality_id)
            if not personality:
                raise ValueError(f"Personality with ID {str(personality_id)} not found")
            setattr(personality, key, value)
            session.add(personality)
            await session.commit()
            return cls._from_db_record(personality)

    @classmethod
    async def list_all(cls) -> list[Self]:
        """List all personalities.

        Returns:
            List of all PersonalityModel instances
        """
        async with get_session() as session:
            results = await session.execute(select(Personality))
            records = results.scalars().all()
            return [cls._from_db_record(personality) for personality in records]

    @classmethod
    async def list_for_user(cls, user_id: str) -> list[Self]:
        """List all personalities a user has access to.

        Args:
            user_id: The ID of the user to get personalities for

        Returns:
            List of PersonalityModel instances the user has access to
        """
        async with get_session() as session:
            # Get all personality IDs the user has access to
            stmt = select(PersonalityUser.personality_id).where(
                PersonalityUser.user_id == user_id
            )
            result = await session.execute(stmt)
            personality_ids = [row[0] for row in result.all()]

            if not personality_ids:
                return []

            # Get all personalities with those IDs
            stmt = select(Personality).where(Personality.id.in_(personality_ids))
            results = await session.execute(stmt)
            records = results.scalars().all()
            return [cls._from_db_record(personality) for personality in records]

    @classmethod
    async def get(cls, personality_id: UUID) -> Self | None:
        """Get a personality by ID.

        Args:
            personality_id: The ID of the personality to get

        Returns:
            The PersonalityModel instance if found, None otherwise
        """
        async with get_session() as session:
            data = await session.get(Personality, personality_id)
            if data:
                return cls._from_db_record(data)
            return None

    @classmethod
    async def get_for_user(cls, personality_id: UUID, user_id: str) -> Self | None:
        """Get a personality by ID if the user has access to it.

        Args:
            personality_id: The ID of the personality to get
            user_id: The ID of the user to check access for

        Returns:
            The PersonalityModel instance if found and user has access, None otherwise
        """
        # Check if the user has access to the personality
        personality_user = await PersonalityUserModel.get(personality_id, user_id)
        if not personality_user:
            return None

        # Get the personality
        return await cls.get(personality_id)

    @classmethod
    async def has_access(cls, personality_id: UUID, user_id: str) -> bool:
        """Check if a user has access to a personality.

        Args:
            personality_id: The ID of the personality to check
            user_id: The ID of the user to check

        Returns:
            True if the user has access, False otherwise
        """
        personality_user = await PersonalityUserModel.get(personality_id, user_id)
        return personality_user is not None

    @classmethod
    async def has_admin_access(cls, personality_id: UUID, user_id: str) -> bool:
        """Check if a user has admin access to a personality.

        Args:
            personality_id: The ID of the personality to check
            user_id: The ID of the user to check

        Returns:
            True if the user has admin access, False otherwise
        """
        personality_user = await PersonalityUserModel.get(personality_id, user_id)
        return personality_user is not None and personality_user.role == "admin"

    @classmethod
    async def add_user(
        cls, personality_id: UUID, user_id: str, role: str = "user"
    ) -> None:
        """Add a user to a personality.

        Args:
            personality_id: The ID of the personality to add the user to
            user_id: The ID of the user to add
            role: The role to assign to the user (default: "user")
        """
        # Check if the user already has access
        personality_user = await PersonalityUserModel.get(personality_id, user_id)
        if personality_user:
            # Update the role if it's different
            if personality_user.role != role:
                await PersonalityUserModel.update_role(personality_id, user_id, role)
            return

        # Add the user
        await PersonalityUserModel.create(
            PersonalityUserModel.CreateParams(
                personality_id=personality_id,
                user_id=user_id,
                role=role,
            )
        )

    @classmethod
    async def remove_user(cls, personality_id: UUID, user_id: str) -> None:
        """Remove a user from a personality.

        Args:
            personality_id: The ID of the personality to remove the user from
            user_id: The ID of the user to remove
        """
        await PersonalityUserModel.delete(personality_id, user_id)

    async def save(
        self,
    ) -> None:
        async with get_session() as session:
            personality = await session.get(Personality, self.id)
            personality.name = self.name
            personality.description = self.description
            personality.context = self.context
            personality.memory = self.memory
            personality.tool_set = self.tool_set
            personality.logo = self.logo
            personality.status = self.status
            # Don't update default field in save
            await session.commit()

    @classmethod
    async def update_status(cls, personality_id: UUID, status: str) -> Self:
        """Update the status of a personality.

        Args:
            personality_id: The ID of the personality to update
            status: The new status (empty string for idle)

        Returns:
            The updated PersonalityModel instance
        """
        return await cls.set(personality_id, "status", status)

    @classmethod
    async def is_idle(cls, personality_id: UUID) -> bool:
        """Check if a personality is idle (status is empty).

        Args:
            personality_id: The ID of the personality to check

        Returns:
            True if the personality is idle, False otherwise
        """
        personality = await cls.get(personality_id)
        return personality is None or not personality.status

    @classmethod
    async def get_many(cls, ids: builtins.list[UUID]) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(Personality).where(Personality.id.in_(ids))
            )
            records = results.scalars().all()
            return [cls._from_db_record(personality) for personality in records]
