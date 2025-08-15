import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.micro_app_data_model import MicroAppDataModel
from neuron_server.models.micro_app_model import MicroAppModel

logger = logging.getLogger(__name__)


class MicroAppAdminDataToolArgs(BaseModel):
    app_id: str = Field(description="UUID of the micro-app")
    operation: str = Field(
        description="""Admin data operation to perform:
        - 'read': Query data records across all users with optional filters
        - 'get': Get a specific record by ID (regardless of owner)
        - 'count': Count records across all users with optional filters
        - 'aggregate': Perform aggregation operations across all users
        """
    )
    record_id: str | None = Field(
        default=None,
        description="Record ID for get operation",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Filters for read/count/aggregate operations. "
            "Supports dot notation for nested fields (e.g., 'address.city'). "
            "Special filter 'user_id' can be used to target specific users."
        ),
    )
    limit: int = Field(
        default=100,
        description="Maximum number of records to return for read operations",
    )
    offset: int = Field(
        default=0,
        description="Number of records to skip for read operations (pagination)",
    )
    field: str | None = Field(
        default=None,
        description="Field name for aggregate operations (sum/avg/min/max)",
    )
    aggregate_operation: str = Field(
        default="count",
        description="Aggregation operation: count, sum, avg, min, max",
    )


class MicroAppAdminDataTool(BaseTool):
    name: str = "micro_app_admin_data"
    description: str = (
        "ADMIN ONLY: Cross-user data operations on micro-apps. "
        "This tool allows administrators to query micro-app data across all users, "
        "which is essential for admin tasks like viewing all tickets in issue tracker. "
        "Requires 'admin' role in user token. "
        "Provides read-only access with operations: read (query), get (by ID), "
        "count, and aggregate. All responses include user ownership information. "
        "Use this for admin oversight and cross-user data analysis."
    )

    args_schema: type[MicroAppAdminDataToolArgs] = MicroAppAdminDataToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0913
        self,
        app_id: str,
        operation: str,
        config: RunnableConfig,
        record_id: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        field: str | None = None,
        aggregate_operation: str = "count",
    ) -> str:
        try:
            # Defense-in-depth: Validate admin role access
            user_id = config["configurable"].get("user_id")
            user_roles = config["configurable"].get("user_roles", [])

            if not user_id:
                raise ValueError("User ID is required")

            if "admin" not in user_roles:
                raise ValueError(
                    "Admin role required. This tool provides cross-user data access "
                    "and is restricted to administrators only."
                )

            logger.info(
                "Admin %s accessing cross-user data for app %s, operation: %s",
                user_id,
                app_id,
                operation,
            )

            app_uuid = UUID(app_id)

            # Verify app exists
            app = await MicroAppModel.get(app_uuid)
            if not app:
                raise ValueError(f"App with ID {app_id} not found")

            # Execute the requested operation
            if operation == "read":
                return await self._admin_read(app, filters, limit, offset)
            if operation == "get":
                return await self._admin_get(app, record_id)
            if operation == "count":
                return await self._admin_count(app, filters)
            if operation == "aggregate":
                return await self._admin_aggregate(
                    app, field, aggregate_operation, filters
                )

            msg = (
                f"Unknown operation: {operation}. Valid operations: "
                "read, get, count, aggregate"
            )
            raise ValueError(msg)

        except ValueError as e:
            logger.error("Validation error in admin data operation: %s", e)
            return f"Error: {e}"
        except Exception as e:
            logger.error("Failed to perform admin data operation: %s", e, exc_info=True)
            return f"Failed to perform admin data operation: {e}"

    async def _admin_read(
        self,
        app: MicroAppModel,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
    ) -> str:
        """Query data records across all users"""
        records = await MicroAppDataModel.admin_query(
            app_id=app.id,
            filters=filters,
            limit=limit,
            offset=offset,
        )

        if not records:
            filter_str = f" with filters {filters}" if filters else ""
            return f"No records found in '{app.name}'{filter_str}"

        # Get total count for pagination info
        total = await MicroAppDataModel.admin_count(app.id, filters)

        # Format records with user ownership information
        records_data = []
        for record in records:
            records_data.append(
                {
                    "id": str(record.id),
                    "user_id": record.user_id,  # Include user ownership
                    "data": record.data,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                }
            )

        pagination_info = (
            f"Showing {len(records)} of {total} total records (cross-user)"
        )
        if offset > 0 or len(records) == limit:
            pagination_info += f" (offset: {offset}, limit: {limit})"

        return f"""Records from '{app.name}' (ADMIN VIEW - ALL USERS):
{pagination_info}

{json.dumps(records_data, indent=2)}"""

    async def _admin_get(self, app: MicroAppModel, record_id: str | None) -> str:
        """Get a specific record by ID regardless of owner"""
        if not record_id:
            raise ValueError("'record_id' parameter is required for get operation")

        record_uuid = UUID(record_id)
        record = await MicroAppDataModel.admin_get(record_uuid)

        if not record:
            return f"Record {record_id} not found in '{app.name}'"

        return f"""Record from '{app.name}' (ADMIN VIEW):
ID: {record.id}
Owner: {record.user_id}
Data: {json.dumps(record.data, indent=2)}
Created at: {record.created_at.isoformat()}
Updated at: {record.updated_at.isoformat()}"""

    async def _admin_count(
        self, app: MicroAppModel, filters: dict[str, Any] | None
    ) -> str:
        """Count records across all users"""
        count = await MicroAppDataModel.admin_count(
            app_id=app.id,
            filters=filters,
        )

        filter_str = f" matching filters {filters}" if filters else ""
        return f"Total records in '{app.name}'{filter_str} (cross-user): {count}"

    async def _admin_aggregate(
        self,
        app: MicroAppModel,
        field: str | None,
        operation: str,
        filters: dict[str, Any] | None,
    ) -> str:
        """Perform aggregation operations across all users"""
        if operation == "count":
            # Special case for count - doesn't need a field
            result = await MicroAppDataModel.admin_count(
                app_id=app.id,
                filters=filters,
            )
            return f"Count of records in '{app.name}' (cross-user): {result}"

        if not field:
            raise ValueError(
                f"'field' parameter is required for {operation} aggregation"
            )

        result = await MicroAppDataModel.admin_aggregate(
            app_id=app.id,
            field=field,
            operation=operation,
            filters=filters,
        )
        return (
            f"{operation.capitalize()} of '{field}' in '{app.name}' "
            f"(cross-user): {result}"
        )
