import warnings
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

import jsonschema
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from neuron_server.database import MicroApp, MicroAppAction, get_session

# Suppress Pydantic field name shadowing warnings for this module
warnings.filterwarnings(
    "ignore",
    message="Field name .* shadows an attribute in parent",
    category=UserWarning,
)


class MicroAppActionModel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(description="Name of the action")
    description: str = Field(description="Description of what the action does")
    action_type: str = Field(
        description="Type of action: create, read, update, delete, aggregate, custom"
    )
    parameters: dict = Field(
        default_factory=dict,
        description="Action-specific parameters and configuration",
    )

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        valid_types = {"create", "read", "update", "delete", "aggregate", "custom"}
        if v not in valid_types:
            raise ValueError(f"Invalid action type. Must be one of: {valid_types}")
        return v


class MicroAppModel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(description="Name of the micro-app")
    description: str = Field(description="Description of the micro-app's purpose")
    schema: dict = Field(description="JSON schema for data validation")
    creator_id: str = Field(description="ID of the user who created this app")
    actions: list[MicroAppActionModel] = Field(
        default_factory=list, description="Available actions for this app"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @field_validator("schema")
    @classmethod
    def validate_json_schema(cls, v: dict) -> dict:
        """Validate that the provided schema is a valid JSON Schema"""
        try:
            # Check if it's a valid JSON Schema by creating a validator
            jsonschema.Draft7Validator.check_schema(v)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e}") from e
        return v

    @classmethod
    async def create(
        cls,
        name: str,
        description: str,
        schema: dict,
        creator_id: str,
        actions: list[MicroAppActionModel],
    ) -> Self:
        """Create a new micro-app with its actions"""
        # Validate the schema
        cls.validate_json_schema(schema)

        async with get_session() as session:
            # Create the app
            app = MicroApp(
                name=name,
                description=description,
                schema=schema,
                creator_id=creator_id,
            )
            session.add(app)
            await session.flush()  # Get the app ID

            # Create the actions
            for action_model in actions:
                action = MicroAppAction(
                    app_id=app.id,
                    name=action_model.name,
                    description=action_model.description,
                    action_type=action_model.action_type,
                    parameters=action_model.parameters,
                )
                session.add(action)

            await session.commit()

            # Return the created app with actions
            return cls(
                id=app.id,
                name=app.name,
                description=app.description,
                schema=app.schema,
                creator_id=app.creator_id,
                actions=actions,
                created_at=app.created_at,
                updated_at=app.updated_at,
            )

    @classmethod
    async def get(cls, app_id: UUID) -> Self | None:
        """Get a micro-app by ID with all its actions"""
        async with get_session() as session:
            result = await session.execute(
                select(MicroApp)
                .where(MicroApp.id == app_id)
                .options(selectinload(MicroApp.actions))
            )
            app = result.scalar_one_or_none()

            if not app:
                return None

            actions = [
                MicroAppActionModel(
                    id=action.id,
                    name=action.name,
                    description=action.description,
                    action_type=action.action_type,
                    parameters=action.parameters,
                )
                for action in app.actions
            ]

            return cls(
                id=app.id,
                name=app.name,
                description=app.description,
                schema=app.schema,
                creator_id=app.creator_id,
                actions=actions,
                created_at=app.created_at,
                updated_at=app.updated_at,
            )

    @classmethod
    async def list_all(cls) -> list[Self]:
        """List all available micro-apps"""
        async with get_session() as session:
            result = await session.execute(
                select(MicroApp).options(selectinload(MicroApp.actions))
            )
            apps = result.scalars().all()

            return [
                cls(
                    id=app.id,
                    name=app.name,
                    description=app.description,
                    schema=app.schema,
                    creator_id=app.creator_id,
                    actions=[
                        MicroAppActionModel(
                            id=action.id,
                            name=action.name,
                            description=action.description,
                            action_type=action.action_type,
                            parameters=action.parameters,
                        )
                        for action in app.actions
                    ],
                    created_at=app.created_at,
                    updated_at=app.updated_at,
                )
                for app in apps
            ]

    @classmethod
    async def list_by_creator(cls, creator_id: str) -> list[Self]:
        """List all micro-apps created by a specific user"""
        async with get_session() as session:
            result = await session.execute(
                select(MicroApp)
                .where(MicroApp.creator_id == creator_id)
                .options(selectinload(MicroApp.actions))
            )
            apps = result.scalars().all()

            return [
                cls(
                    id=app.id,
                    name=app.name,
                    description=app.description,
                    schema=app.schema,
                    creator_id=app.creator_id,
                    actions=[
                        MicroAppActionModel(
                            id=action.id,
                            name=action.name,
                            description=action.description,
                            action_type=action.action_type,
                            parameters=action.parameters,
                        )
                        for action in app.actions
                    ],
                    created_at=app.created_at,
                    updated_at=app.updated_at,
                )
                for app in apps
            ]

    @classmethod
    async def update(cls, app_id: UUID, updates: dict[str, str]) -> bool:
        """Update the app's name and/or description (maintains schema immutability)"""
        async with get_session() as session:
            app = await session.get(MicroApp, app_id)
            if not app:
                return False

            # Update allowed fields only (maintain schema immutability)
            if "name" in updates:
                app.name = updates["name"]
            if "description" in updates:
                app.description = updates["description"]

            await session.commit()
            return True

    @classmethod
    async def delete(cls, app_id: UUID) -> bool:
        """Delete a micro-app and all associated data"""
        async with get_session() as session:
            app = await session.get(MicroApp, app_id)
            if not app:
                return False

            await session.delete(app)
            await session.commit()
            return True
