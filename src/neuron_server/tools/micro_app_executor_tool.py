import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.micro_app_data_model import MicroAppDataModel
from neuron_server.models.micro_app_model import MicroAppActionModel, MicroAppModel

logger = logging.getLogger(__name__)


class MicroAppExecutorToolArgs(BaseModel):
    app_id: str = Field(description="UUID of the micro-app to execute action on")
    action_name: str = Field(description="Name of the action to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="""Parameters for the action. Common parameters:
        - For 'create': {"data": {...}} - The data object to create
        - For 'read': {"filters": {...}, "limit": 10, "offset": 0}
        - For 'update': {"record_id": "...", "data": {...}, "partial": true}
        - For 'delete': {"record_id": "..."} - ID of record to delete
        - For 'aggregate': {"field": "...", "operation": "sum|avg|min|max|count",
           "filters": {...}}
        - For 'custom': Action-specific parameters defined in the app
        """,
    )


class MicroAppExecutorTool(BaseTool):
    name: str = "micro_app_executor"
    description: str = """Execute actions on a micro-app's data.

    This tool executes predefined actions on micro-app data with automatic:
    - JSON schema validation
    - User data segmentation (users can only access their own data)
    - Type checking and constraints enforcement

    Use the micro_app_manager tool to list available apps and their actions.
    """

    args_schema: type[MicroAppExecutorToolArgs] = MicroAppExecutorToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        app_id: str,
        action_name: str,
        parameters: dict[str, Any],
        config: RunnableConfig,
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            # Convert string UUID to UUID object
            app_uuid = UUID(app_id)

            # Get the app and its actions
            app = await MicroAppModel.get(app_uuid)
            if not app:
                raise ValueError(f"App with ID {app_id} not found")

            # Find the requested action
            action = next((a for a in app.actions if a.name == action_name), None)
            if not action:
                available_actions = ", ".join([a.name for a in app.actions])
                msg = (
                    f"Action '{action_name}' not found. "
                    f"Available: {available_actions}"
                )
                raise ValueError(msg)

            # Execute based on action type
            return await self._execute_action(
                app=app,
                action=action,
                parameters=parameters,
                user_id=user_id,
            )


        except ValueError as e:
            logger.error("Validation error executing action: %s", e)
            return f"Error: {e}"
        except Exception as e:
            logger.error("Failed to execute action: %s", e, exc_info=True)
            return f"Failed to execute action: {e}"

    async def _execute_action(
        self,
        app: MicroAppModel,
        action: MicroAppActionModel,
        parameters: dict,
        user_id: str,
    ) -> str:
        """Execute a specific action based on its type"""
        action_type = action.action_type

        if action_type == "create":
            return await self._execute_create(app, parameters, user_id)
        if action_type == "read":
            return await self._execute_read(app, parameters, user_id)
        if action_type == "update":
            return await self._execute_update(app, parameters, user_id)
        if action_type == "delete":
            return await self._execute_delete(app, parameters, user_id)
        if action_type == "aggregate":
            return await self._execute_aggregate(app, parameters, user_id)
        if action_type == "custom":
            return await self._execute_custom(app, action, parameters, user_id)
        raise ValueError(f"Unknown action type: {action_type}")

    async def _execute_create(
        self, app: MicroAppModel, parameters: dict, user_id: str
    ) -> str:
        """Execute a create action"""
        data = parameters.get("data")
        if not data:
            raise ValueError("'data' parameter is required for create action")

        # Handle bulk create if data is a list
        if isinstance(data, list):
            records = await MicroAppDataModel.bulk_create(
                app_id=app.id,
                user_id=user_id,
                data_list=data,
            )
            return f"Successfully created {len(records)} records in '{app.name}'"
        record = await MicroAppDataModel.create(
            app_id=app.id,
            user_id=user_id,
            data=data,
        )
        return f"Successfully created record (ID: {record.id}) in '{app.name}'"

    async def _execute_read(
        self, app: MicroAppModel, parameters: dict, user_id: str
    ) -> str:
        """Execute a read/query action"""
        filters = parameters.get("filters", {})
        limit = parameters.get("limit", 100)
        offset = parameters.get("offset", 0)

        records = await MicroAppDataModel.query(
            app_id=app.id,
            user_id=user_id,
            filters=filters,
            limit=limit,
            offset=offset,
        )

        if not records:
            return f"No records found in '{app.name}' matching the criteria"

        # Format records as JSON for readability
        records_data = [
            {
                "id": str(record.id),
                "data": record.data,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
            }
            for record in records
        ]

        result = json.dumps(records_data, indent=2)
        return f"Found {len(records)} record(s) in '{app.name}':\n{result}"

    async def _execute_update(
        self, app: MicroAppModel, parameters: dict, user_id: str
    ) -> str:
        """Execute an update action"""
        record_id = parameters.get("record_id")
        data = parameters.get("data")
        partial = parameters.get("partial", False)

        if not record_id:
            raise ValueError("'record_id' parameter is required for update action")
        if not data:
            raise ValueError("'data' parameter is required for update action")

        record_uuid = UUID(record_id)
        updated = await MicroAppDataModel.update(
            record_id=record_uuid,
            user_id=user_id,
            data=data,
            partial=partial,
        )

        if not updated:
            return (
                f"Record {record_id} not found or "
                "you don't have permission to update it"
            )

        return f"Successfully updated record {record_id} in '{app.name}'"

    async def _execute_delete(
        self, app: MicroAppModel, parameters: dict, user_id: str
    ) -> str:
        """Execute a delete action"""
        record_id = parameters.get("record_id")
        if not record_id:
            raise ValueError("'record_id' parameter is required for delete action")

        record_uuid = UUID(record_id)
        deleted = await MicroAppDataModel.delete(
            record_id=record_uuid,
            user_id=user_id,
        )

        if not deleted:
            return (
                f"Record {record_id} not found or "
                "you don't have permission to delete it"
            )

        return f"Successfully deleted record {record_id} from '{app.name}'"

    async def _execute_aggregate(
        self, app: MicroAppModel, parameters: dict, user_id: str
    ) -> str:
        """Execute an aggregation action"""
        field = parameters.get("field")
        operation = parameters.get("operation", "count")
        filters = parameters.get("filters", {})

        if operation == "count":
            # Special case for count - doesn't need a field
            result = await MicroAppDataModel.count(
                app_id=app.id,
                user_id=user_id,
                filters=filters,
            )
            return f"Count of records in '{app.name}': {result}"
        if not field:
            raise ValueError(
                f"'field' parameter is required for {operation} aggregation"
            )

        result = await MicroAppDataModel.aggregate(
            app_id=app.id,
            user_id=user_id,
            field=field,
            operation=operation,
            filters=filters,
        )
        return f"{operation.capitalize()} of '{field}' in '{app.name}': {result}"

    async def _execute_custom(
        self,
        app: MicroAppModel,
        action: MicroAppActionModel,
        parameters: dict,
        user_id: str,
    ) -> str:
        """Execute a custom action defined by the app"""
        # Custom actions can combine multiple operations
        # This is a placeholder for more complex custom logic
        custom_params = action.parameters

        # Example: A custom "complete_all" action might update multiple records
        if "batch_operation" in custom_params:
            operation = custom_params["batch_operation"]
            if operation == "update_all":
                filters = parameters.get("filters", {})
                update_data = parameters.get("data", {})

                # Query matching records
                records = await MicroAppDataModel.query(
                    app_id=app.id,
                    user_id=user_id,
                    filters=filters,
                )

                # Update each record
                updated_count = 0
                for record in records:
                    updated = await MicroAppDataModel.update(
                        record_id=record.id,
                        user_id=user_id,
                        data=update_data,
                        partial=True,
                    )
                    if updated:
                        updated_count += 1

                return f"Updated {updated_count} records in '{app.name}'"

        # Default custom action response
        return f"Executed custom action '{action.name}' on '{app.name}'"
