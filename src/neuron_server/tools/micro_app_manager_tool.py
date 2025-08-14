import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.micro_app_model import MicroAppModel

logger = logging.getLogger(__name__)


class MicroAppManagerToolArgs(BaseModel):
    operation: str = Field(
        description="""Operation to perform:
        - 'list': List all available micro-apps
        - 'list_mine': List micro-apps created by the current user
        - 'get': Get details of a specific app (requires app_id)
        - 'update_name': Update the app name (requires app_id and new_name)
        - 'update_descriptions': Update field descriptions in app schema
          (requires app_id and field_descriptions)
        - 'delete': Delete a micro-app (requires app_id, only creator can delete)
        """
    )
    app_id: str | None = Field(
        default=None,
        description=(
            "UUID of the micro-app (required for 'get', 'update_name', "
            "'update_descriptions', and 'delete' operations)"
        ),
    )
    new_name: str | None = Field(
        default=None,
        description="New name for the app (used with 'update_name')",
    )
    field_descriptions: dict[str, str] | None = Field(
        default=None,
        description=(
            "Field name to description mapping for updating schema descriptions "
            "(used with 'update_descriptions')"
        ),
    )


class MicroAppManagerTool(BaseTool):
    name: str = "micro_app_manager"
    description: str = """Manage micro-apps: list available apps, get app details,
    update field descriptions, or delete apps.

    This tool allows you to:
    - Discover available micro-apps and their capabilities
    - Get detailed information about app schemas and actions
    - Update field descriptions to provide better instructions for agents
    - Delete apps you've created

    Field descriptions are important as they serve as instructions for agents
    using the apps.
    """

    args_schema: type[MicroAppManagerToolArgs] = MicroAppManagerToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0911, PLR0912
        self,
        operation: str,
        config: RunnableConfig,
        app_id: str | None = None,
        new_name: str | None = None,
        field_descriptions: dict[str, str] | None = None,
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            if operation == "list":
                return await self._list_all_apps()
            if operation == "list_mine":
                return await self._list_user_apps(user_id)
            if operation == "get":
                if not app_id:
                    raise ValueError("app_id is required for 'get' operation")
                return await self._get_app_details(app_id)
            if operation == "update_name":
                if not app_id:
                    msg = "app_id is required for 'update_name' operation"
                    raise ValueError(msg)
                if not new_name:
                    msg = "new_name is required for 'update_name' operation"
                    raise ValueError(msg)
                return await self._update_name(app_id, new_name, user_id)
            if operation == "update_descriptions":
                if not app_id:
                    raise ValueError(
                        "app_id is required for 'update_descriptions' operation"
                    )
                if not field_descriptions:
                    raise ValueError(
                        "field_descriptions is required for "
                        "'update_descriptions' operation"
                    )
                return await self._update_descriptions(
                    app_id, field_descriptions, user_id
                )
            if operation == "delete":
                if not app_id:
                    raise ValueError("app_id is required for 'delete' operation")
                return await self._delete_app(app_id, user_id)
            raise ValueError(
                f"Unknown operation: {operation}. Valid operations: "
                "list, list_mine, get, update_name, update_descriptions, delete"
            )

        except ValueError as e:
            logger.error("Validation error in micro-app manager: %s", e)
            return f"Error: {e}"
        except Exception as e:
            logger.error("Failed to manage micro-app: %s", e, exc_info=True)
            return f"Failed to manage micro-app: {e}"

    async def _list_all_apps(self) -> str:
        """List all available micro-apps"""
        apps = await MicroAppModel.list_all()

        if not apps:
            return "No micro-apps available. Use micro_app_create to create one."

        app_list = []
        for app in apps:
            action_names = [a.name for a in app.actions]
            app_list.append(
                f"- {app.name} (ID: {app.id})\n"
                f"  Description: {app.description}\n"
                f"  Actions: {', '.join(action_names)}\n"
                f"  Created by: {app.creator_id}"
            )

        return f"Available micro-apps ({len(apps)} total):\n\n" + "\n\n".join(app_list)

    async def _list_user_apps(self, user_id: str) -> str:
        """List micro-apps created by the current user"""
        apps = await MicroAppModel.list_by_creator(user_id)

        if not apps:
            return (
                "You haven't created any micro-apps yet. "
                "Use micro_app_create to create one."
            )

        app_list = []
        for app in apps:
            action_names = [a.name for a in app.actions]
            app_list.append(
                f"- {app.name} (ID: {app.id})\n"
                f"  Description: {app.description}\n"
                f"  Actions: {', '.join(action_names)}\n"
                f"  Created at: {app.created_at.isoformat()}"
            )

        return f"Your micro-apps ({len(apps)} total):\n\n" + "\n\n".join(app_list)

    async def _get_app_details(self, app_id: str) -> str:
        """Get detailed information about a specific app"""
        app_uuid = UUID(app_id)
        app = await MicroAppModel.get(app_uuid)

        if not app:
            return f"App with ID {app_id} not found"

        # Format schema for readability
        schema_str = json.dumps(app.schema, indent=2)

        # Format actions
        actions_str = []
        for action in app.actions:
            params_str = (
                json.dumps(action.parameters, indent=4) if action.parameters else "None"
            )
            actions_str.append(
                f"  - {action.name} ({action.action_type})\n"
                f"    Description: {action.description}\n"
                f"    Parameters: {params_str}"
            )

        return f"""Micro-app Details:

Name: {app.name}
ID: {app.id}
Description: {app.description}
Creator: {app.creator_id}
Created: {app.created_at.isoformat()}
Updated: {app.updated_at.isoformat()}

Schema:
{schema_str}

Actions ({len(app.actions)}):
{chr(10).join(actions_str)}

To use this app, call micro_app_executor with app_id={app.id} and the desired " \
"action_name."""

    async def _update_name(self, app_id: str, new_name: str, user_id: str) -> str:
        """Update the app's name (only if created by the user)"""
        app_uuid = UUID(app_id)
        app = await MicroAppModel.get(app_uuid)

        if not app:
            return f"App with ID {app_id} not found"

        if app.creator_id != user_id:
            return (
                f"You can only rename apps you created. "
                f"This app was created by {app.creator_id}"
            )

        success = await MicroAppModel.update_name(app_uuid, new_name)

        if not success:
            return f"Failed to update name for app with ID {app_id}"

        return f"Successfully updated app name to '{new_name}'"

    async def _update_descriptions(
        self, app_id: str, field_descriptions: dict[str, str], user_id: str
    ) -> str:
        """Update field descriptions in the app's schema.

        Only the creator can update field descriptions.
        """
        app_uuid = UUID(app_id)
        app = await MicroAppModel.get(app_uuid)

        if not app:
            return f"App with ID {app_id} not found"

        if app.creator_id != user_id:
            return (
                f"You can only update apps you created. "
                f"This app was created by {app.creator_id}"
            )

        success = await MicroAppModel.update_descriptions(app_uuid, field_descriptions)

        if not success:
            return f"Failed to update descriptions for app with ID {app_id}"

        updated_fields = ", ".join(field_descriptions.keys())
        return f"Successfully updated descriptions for fields: {updated_fields}"

    async def _delete_app(self, app_id: str, user_id: str) -> str:
        """Delete a micro-app (only if created by the user)"""
        app_uuid = UUID(app_id)
        app = await MicroAppModel.get(app_uuid)

        if not app:
            return f"App with ID {app_id} not found"

        if app.creator_id != user_id:
            return (
                f"You can only delete apps you created. "
                f"This app was created by {app.creator_id}"
            )

        success = await MicroAppModel.delete(app_uuid)

        if success:
            return (
                f"Successfully deleted micro-app '{app.name}' (ID: {app_id}) "
                "and all associated data"
            )
        return f"Failed to delete app with ID {app_id}"
