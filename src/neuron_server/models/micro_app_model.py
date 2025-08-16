import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

import jsonschema
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from neuron_server.database import MicroApp, MicroAppAction, get_session
from neuron_server.models.display_config_model import DisplayConfig

# Suppress Pydantic field name shadowing warnings for this module
warnings.filterwarnings(
    "ignore",
    message="Field name .* shadows an attribute in parent",
    category=UserWarning,
)


@dataclass
class CreateMicroAppData:
    """Data class for micro-app creation parameters"""

    name: str
    description: str
    schema: dict
    creator_id: str
    actions: list["MicroAppActionModel"]
    display_schema: dict | None = None


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
    display_schema: dict | None = Field(
        default=None, description="Display configuration for frontend rendering"
    )
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

    @field_validator("display_schema")
    @classmethod
    def validate_display_schema(cls, v: dict | None) -> dict | None:
        """Validate display schema structure using Pydantic model"""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("Display schema must be a dictionary")

        # Use Pydantic model for validation
        try:
            DisplayConfig.model_validate(v)
        except Exception as e:
            raise ValueError(f"Invalid display schema: {e}") from e

        return v

    @classmethod
    async def create(cls, data: CreateMicroAppData) -> Self:
        """Create a new micro-app with its actions"""
        # Validate the schemas
        cls.validate_json_schema(data.schema)
        if data.display_schema is not None:
            cls.validate_display_schema(data.display_schema)

        async with get_session() as session:
            # Create the app
            app = MicroApp(
                name=data.name,
                description=data.description,
                schema=data.schema,
                display_schema=data.display_schema,
                creator_id=data.creator_id,
            )
            session.add(app)
            await session.flush()  # Get the app ID

            # Create the actions
            for action_model in data.actions:
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
                display_schema=app.display_schema,
                creator_id=app.creator_id,
                actions=data.actions,
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
                display_schema=app.display_schema,
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
                    display_schema=app.display_schema,
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
                    display_schema=app.display_schema,
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
    async def update(cls, app_id: UUID, updates: dict[str, str | dict | None]) -> bool:
        """Update name, description, and/or display_schema"""
        async with get_session() as session:
            app = await session.get(MicroApp, app_id)
            if not app:
                return False

            # Update allowed fields only (maintain schema immutability)
            if "name" in updates:
                app.name = updates["name"]
            if "description" in updates:
                app.description = updates["description"]
            if "display_schema" in updates:
                display_schema = updates["display_schema"]
                if display_schema is not None:
                    cls.validate_display_schema(display_schema)
                app.display_schema = display_schema

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
