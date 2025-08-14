import asyncio
import logging
import warnings
from typing import Any

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, field_validator

from neuron_server.models.micro_app_model import MicroAppActionModel, MicroAppModel

# Suppress Pydantic field name shadowing warnings for this module
warnings.filterwarnings(
    "ignore",
    message="Field name .* shadows an attribute in parent",
    category=UserWarning
)

logger = logging.getLogger(__name__)


class MicroAppActionInput(BaseModel):
    name: str = Field(description="Name of the action")
    description: str = Field(description="Description of what the action does")
    action_type: str = Field(
        description="Type of action: create, read, update, delete, aggregate, custom"
    )
    parameters: dict = Field(
        default_factory=dict,
        description="Action-specific parameters (e.g., filters, fields, operations)",
    )


class MicroAppCreateToolArgs(BaseModel):
    name: str = Field(description="Name of the micro-app")
    description: str = Field(
        description="Description of the micro-app's purpose and functionality"
    )
    schema: dict = Field(
        description="""JSON Schema defining the structure of data for this app.
        Example: {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the item"},
                "completed": {
                    "type": "boolean",
                    "description": "Whether item is completed"
                },
                "priority": {"type": "integer", "minimum": 1, "maximum": 5}
            },
            "required": ["title"]
        }"""
    )
    actions: list[MicroAppActionInput] = Field(
        description="""List of actions that can be performed on the app's data.
        Example actions:
        - {name: "add_todo", description: "Add a new todo item", action_type: "create"}
        - {name: "list_todos", description: "List all todos", action_type: "read",
           parameters: {"filters": ["completed", "priority"]}}
        - {name: "complete_todo", description: "Mark todo as complete",
           action_type: "update"}
        - {name: "delete_todo", description: "Remove a todo", action_type: "delete"}
        - {name: "count_by_priority", description: "Count todos by priority",
           action_type: "aggregate", parameters: {"operation": "count",
           "group_by": "priority"}}
        """
    )

    @field_validator("schema")
    @classmethod
    def validate_schema(cls, v: dict) -> dict:
        """Ensure the schema is a valid JSON Schema"""
        if "type" not in v:
            raise ValueError("Schema must have a 'type' field")
        if v["type"] not in ["object", "array"]:
            raise ValueError("Schema type must be 'object' or 'array'")
        return v


class MicroAppCreateTool(BaseTool):
    name: str = "micro_app_create"
    description: str = """Create a new micro-app with a custom data schema and actions.

    This tool allows agents to create structured data storage applications like:
    - Todo lists with custom fields
    - Issue tracking systems
    - Inventory management
    - Custom forms and surveys
    - Any application requiring structured data storage

    The app definition is immutable after creation (except field descriptions).
    Apps are shared across users, but data is user-segmented.
    """

    args_schema: type[MicroAppCreateToolArgs] = MicroAppCreateToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        name: str,
        description: str,
        schema: dict,
        actions: list[MicroAppActionInput],
        config: RunnableConfig,
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            # Convert action inputs to models
            action_models = []
            for action in actions:
                if isinstance(action, dict):
                    # Handle dict input
                    action_models.append(
                        MicroAppActionModel(
                            name=action["name"],
                            description=action["description"],
                            action_type=action["action_type"],
                            parameters=action.get("parameters", {}),
                        )
                    )
                else:
                    # Handle MicroAppActionInput object
                    action_models.append(
                        MicroAppActionModel(
                            name=action.name,
                            description=action.description,
                            action_type=action.action_type,
                            parameters=action.parameters,
                        )
                    )

            # Create the micro-app
            app = await MicroAppModel.create(
                name=name,
                description=description,
                schema=schema,
                creator_id=user_id,
                actions=action_models,
            )

            # Generate a summary of available actions
            action_summary = "\n".join(
                [
                    f"  - {a.name}: {a.description} ({a.action_type})"
                    for a in app.actions
                ]
            )

            logger.info(
                "Created micro-app: %s (ID: %s) with %d actions",
                app.name,
                app.id,
                len(app.actions),
            )

            return f"""Successfully created micro-app '{app.name}' (ID: {app.id})

Description: {app.description}

Available actions:
{action_summary}

Schema fields:
{", ".join(schema.get("properties", {}).keys()) if "properties" in schema else "None"}

Use micro_app_executor with app_id={app.id} to perform these actions."""

        except ValueError as e:
            logger.error("Validation error creating micro-app: %s", e)
            raise ValueError(f"Failed to create micro-app: {e}") from e
        except Exception as e:
            logger.error("Failed to create micro-app: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create micro-app: {e}") from e
