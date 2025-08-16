import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.display_config_model import DisplayConfig
from neuron_server.models.micro_app_model import MicroAppModel

logger = logging.getLogger(__name__)

# Constants
MAX_LIST_FIELDS = 3
TEXTAREA_MIN_LENGTH = 100


class MicroAppDisplayConfigToolArgs(BaseModel):
    operation: str = Field(
        description="""Operation to perform:
        - 'create': Generate new display config from app JSON schema
        - 'update': Update existing display config (requires config_data)
        - 'get': Show current display configuration
        """
    )
    app_id: str = Field(description="UUID of the micro-app to configure")
    config_data: dict | None = Field(
        default=None,
        description=(
            "Display configuration data (required for 'update'). "
            "Must include 'views' and 'components' sections. "
            "Example: {'views': {'list': {'fields': ['name']}, "
            "'detail': {'fields': ['name', 'description']}}, "
            "'components': {'name': {'type': 'input', 'label': 'Name'}}}"
        ),
    )
    list_fields: list[str] | None = Field(
        default=None,
        description=(
            "Fields to show in list view (for 'create' operation). "
            "If not provided, will auto-select up to 3 fields from schema."
        ),
    )


class MicroAppDisplayConfigTool(BaseTool):
    name: str = "micro_app_display_config"
    description: str = """Create and manage display configurations for micro-apps.

    This tool allows you to:
    - Generate display configs from the app's JSON schema with smart defaults
    - Update existing display configurations
    - View current display configuration

    Display configs define how the frontend renders forms, lists, and detail views.
    The tool automatically creates valid configurations based on the JSON schema.
    """

    args_schema: type[MicroAppDisplayConfigToolArgs] = MicroAppDisplayConfigToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        operation: str,
        app_id: str,
        config: RunnableConfig,
        config_data: dict | None = None,
        list_fields: list[str] | None = None,
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            if operation == "create":
                return await self._create_display_config(app_id, user_id, list_fields)
            if operation == "update":
                if not config_data:
                    raise ValueError("config_data is required for 'update' operation")
                return await self._update_display_config(app_id, user_id, config_data)
            if operation == "get":
                return await self._get_display_config(app_id)
            raise ValueError(
                f"Unknown operation: {operation}. Valid operations: create, update, get"
            )

        except ValueError as e:
            logger.error("Validation error in display config tool: %s", e)
            return f"Error: {e}"
        except Exception as e:
            logger.error("Failed to manage display config: %s", e, exc_info=True)
            return f"Failed to manage display config: {e}"

    async def _create_display_config(
        self, app_id: str, user_id: str, list_fields: list[str] | None = None
    ) -> str:
        """Generate new display config from app's JSON schema"""
        app_uuid = UUID(app_id)
        app = await MicroAppModel.get(app_uuid)

        if not app:
            return f"App with ID {app_id} not found"

        if app.creator_id != user_id:
            return (
                f"You can only configure display for apps you created. "
                f"This app was created by {app.creator_id}"
            )

        # Generate display config from JSON schema
        display_config = self._generate_display_config_from_schema(
            app.schema, app.name, list_fields
        )

        # Validate the generated config using Pydantic
        try:
            DisplayConfig.model_validate(display_config)
        except Exception as e:
            return f"Generated display config is invalid: {e}"

        # Update the app with the new display config
        success = await MicroAppModel.update(
            app_uuid, {"display_schema": display_config}
        )

        if not success:
            return f"Failed to save display config for app {app_id}"

        return f"""Successfully created display configuration for '{app.name}'.

Generated configuration:
{json.dumps(display_config, indent=2)}

The app now has functional list and detail views in the frontend."""

    async def _update_display_config(
        self, app_id: str, user_id: str, config_data: dict
    ) -> str:
        """Update existing display config"""
        app_uuid = UUID(app_id)
        app = await MicroAppModel.get(app_uuid)

        if not app:
            return f"App with ID {app_id} not found"

        if app.creator_id != user_id:
            return (
                f"You can only configure display for apps you created. "
                f"This app was created by {app.creator_id}"
            )

        # Validate the provided config using Pydantic
        try:
            DisplayConfig.model_validate(config_data)
        except Exception as e:
            return f"Invalid display config: {e}"

        # Update the app
        success = await MicroAppModel.update(app_uuid, {"display_schema": config_data})

        if not success:
            return f"Failed to update display config for app {app_id}"

        return f"Successfully updated display configuration for '{app.name}'"

    async def _get_display_config(self, app_id: str) -> str:
        """Show current display configuration"""
        app_uuid = UUID(app_id)
        app = await MicroAppModel.get(app_uuid)

        if not app:
            return f"App with ID {app_id} not found"

        if not app.display_schema:
            return (
                f"No display configuration found for '{app.name}'. "
                "Use 'create' operation to generate one."
            )

        return f"""Current display configuration for '{app.name}':

{json.dumps(app.display_schema, indent=2)}"""

    def _generate_display_config_from_schema(
        self, json_schema: dict, app_name: str, list_fields: list[str] | None = None
    ) -> dict:
        """Generate display config from JSON schema"""
        properties = json_schema.get("properties", {})
        required_fields = json_schema.get("required", [])

        components = {}
        all_fields = []

        for position, (field_name, field_schema) in enumerate(properties.items()):
            all_fields.append(field_name)
            components[field_name] = self._create_component_config(
                field_name, field_schema, required_fields, position
            )

        final_list_fields = self._select_list_fields(all_fields, list_fields)

        return {
            "views": {
                "list": {
                    "fields": final_list_fields,
                    "title": f"{app_name} List",
                },
                "detail": {
                    "fields": all_fields,
                    "title": f"{app_name} Details",
                },
            },
            "components": components,
        }

    def _create_component_config(
        self,
        field_name: str,
        field_schema: dict,
        required_fields: list[str],
        position: int,
    ) -> dict:
        """Create component configuration for a field"""
        component_type = self._get_component_type_from_schema(field_schema)

        component_config = {
            "type": component_type,
            "label": self._format_label(field_name),
            "required": field_name in required_fields,
            "position": position,
        }

        # Add placeholder for input fields
        if component_type in ["input", "email", "textarea"]:
            component_config["placeholder"] = (
                f"Enter {component_config['label'].lower()}"
            )

        # Add options for select fields
        if component_type == "select" and "enum" in field_schema:
            component_config["options"] = [
                {"value": str(value), "label": self._format_label(str(value))}
                for value in field_schema["enum"]
            ]

        # Add validation constraints
        validation = self._extract_validation_constraints(field_schema)
        if validation:
            component_config["validation"] = validation

        return component_config

    def _extract_validation_constraints(self, field_schema: dict) -> dict:
        """Extract validation constraints from field schema"""
        validation = {}
        constraint_mappings = {
            "minLength": "minLength",
            "maxLength": "maxLength",
            "minimum": "min",
            "maximum": "max",
            "pattern": "pattern",
        }

        for schema_key, validation_key in constraint_mappings.items():
            if schema_key in field_schema:
                validation[validation_key] = field_schema[schema_key]

        return validation

    def _select_list_fields(
        self, all_fields: list[str], list_fields: list[str] | None
    ) -> list[str]:
        """Select fields for list view"""
        if list_fields:
            # Use provided list fields (validate they exist)
            valid_list_fields = [f for f in list_fields if f in all_fields]
            if not valid_list_fields:
                raise ValueError(
                    f"None of the provided list_fields exist in schema: {list_fields}"
                )
            return valid_list_fields

        # Auto-select up to 3 fields, prioritizing common names
        priority_fields = [
            "name",
            "title",
            "label",
            "description",
            "status",
            "category",
        ]
        selected_fields = []

        # First, add priority fields that exist
        for field in priority_fields:
            if field in all_fields and len(selected_fields) < MAX_LIST_FIELDS:
                selected_fields.append(field)

        # Then add remaining fields up to MAX_LIST_FIELDS total
        for field in all_fields:
            if field not in selected_fields and len(selected_fields) < MAX_LIST_FIELDS:
                selected_fields.append(field)

        return selected_fields

    def _get_component_type_from_schema(self, field_schema: dict) -> str:
        """Map JSON Schema types to component types"""
        # Check for enum first (highest priority)
        if "enum" in field_schema:
            return "select"

        field_type = field_schema.get("type", "string")
        field_format = field_schema.get("format")

        # Type-based mappings
        type_mappings = {
            "boolean": "checkbox",
            "integer": "number",
            "number": "number",
        }

        if field_type in type_mappings:
            return type_mappings[field_type]

        # String type with format or length considerations
        if field_type == "string":
            return self._get_string_component_type(field_schema, field_format)

        # Default fallback
        return "input"

    def _get_string_component_type(
        self, field_schema: dict, field_format: str | None
    ) -> str:
        """Determine component type for string fields based on format and constraints"""
        if field_format == "email":
            return "email"
        if field_format in ["date", "date-time"]:
            return "date"
        if field_schema.get("maxLength", 0) > TEXTAREA_MIN_LENGTH:
            return "textarea"
        return "input"

    def _format_label(self, field_name: str) -> str:
        """Format field name into a human-readable label"""
        return field_name.replace("_", " ").replace("-", " ").title()
