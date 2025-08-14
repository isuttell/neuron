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


class MicroAppDataToolArgs(BaseModel):
    app_id: str = Field(description="UUID of the micro-app")
    operation: str = Field(
        description="""Data operation to perform:
        - 'create': Create a new data record
        - 'read': Query data records with optional filters
        - 'get': Get a specific record by ID
        - 'update': Update an existing record
        - 'delete': Delete a record
        - 'count': Count records with optional filters
        - 'bulk_create': Create multiple records at once
        """
    )
    data: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "Data for create/update operations. "
            "Single dict for create/update, list for bulk_create"
        ),
    )
    record_id: str | None = Field(
        default=None,
        description="Record ID for get/update/delete operations",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Filters for read/count operations. "
            "Supports dot notation for nested fields (e.g., 'address.city')"
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
    partial: bool = Field(
        default=False,
        description=(
            "For update operations: if true, merge with existing data; "
            "if false, replace entirely"
        ),
    )


class MicroAppDataTool(BaseTool):
    name: str = "micro_app_data"
    description: str = (
        "Direct data operations on micro-apps with full control "
        "over CRUD operations. "
        "This tool provides low-level access to micro-app data with: "
        "direct CRUD operations, bulk operations, advanced filtering "
        "with dot notation, pagination, automatic schema validation, "
        "and user data isolation. "
        "Use this when you need fine-grained control over data operations. "
        "For predefined actions, use micro_app_executor instead."
    )

    args_schema: type[MicroAppDataToolArgs] = MicroAppDataToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0911, PLR0913
        self,
        app_id: str,
        operation: str,
        config: RunnableConfig,
        data: dict[str, Any] | list[dict[str, Any]] | None = None,
        record_id: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        partial: bool = False,
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            app_uuid = UUID(app_id)

            # Verify app exists
            app = await MicroAppModel.get(app_uuid)
            if not app:
                raise ValueError(f"App with ID {app_id} not found")

            # Execute the requested operation
            if operation == "create":
                return await self._create(app, data, user_id)
            if operation == "read":
                return await self._read(app, filters, limit, offset, user_id)
            if operation == "get":
                return await self._get(app, record_id, user_id)
            if operation == "update":
                return await self._update(app, record_id, data, partial, user_id)
            if operation == "delete":
                return await self._delete(app, record_id, user_id)
            if operation == "count":
                return await self._count(app, filters, user_id)
            if operation == "bulk_create":
                return await self._bulk_create(app, data, user_id)
            msg = (
                f"Unknown operation: {operation}. Valid operations: "
                "create, read, get, update, delete, count, bulk_create"
            )
            raise ValueError(msg)

        except ValueError as e:
            logger.error("Validation error in data operation: %s", e)
            return f"Error: {e}"
        except Exception as e:
            logger.error("Failed to perform data operation: %s", e, exc_info=True)
            return f"Failed to perform data operation: {e}"

    async def _create(
        self, app: MicroAppModel, data: dict[str, Any] | None, user_id: str
    ) -> str:
        """Create a new data record"""
        if not data or not isinstance(data, dict):
            msg = "'data' parameter (dict) is required for create operation"
            raise ValueError(msg)

        record = await MicroAppDataModel.create(
            app_id=app.id,
            user_id=user_id,
            data=data,
        )

        return f"""Successfully created record in '{app.name}':
ID: {record.id}
Data: {json.dumps(record.data, indent=2)}
Created at: {record.created_at.isoformat()}"""

    async def _read(
        self,
        app: MicroAppModel,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        user_id: str,
    ) -> str:
        """Query data records"""
        records = await MicroAppDataModel.query(
            app_id=app.id,
            user_id=user_id,
            filters=filters,
            limit=limit,
            offset=offset,
        )

        if not records:
            filter_str = f" with filters {filters}" if filters else ""
            return f"No records found in '{app.name}'{filter_str}"

        # Get total count for pagination info
        total = await MicroAppDataModel.count(app.id, user_id, filters)

        # Format records
        records_data = []
        for record in records:
            records_data.append(
                {
                    "id": str(record.id),
                    "data": record.data,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                }
            )

        pagination_info = f"Showing {len(records)} of {total} total records"
        if offset > 0 or len(records) == limit:
            pagination_info += f" (offset: {offset}, limit: {limit})"

        return f"""Records from '{app.name}':
{pagination_info}

{json.dumps(records_data, indent=2)}"""

    async def _get(
        self, app: MicroAppModel, record_id: str | None, user_id: str
    ) -> str:
        """Get a specific record by ID"""
        if not record_id:
            raise ValueError("'record_id' parameter is required for get operation")

        record_uuid = UUID(record_id)
        record = await MicroAppDataModel.get(record_uuid, user_id)

        if not record:
            return (
                f"Record {record_id} not found in '{app.name}' or "
                "you don't have permission to access it"
            )

        return f"""Record from '{app.name}':
ID: {record.id}
Data: {json.dumps(record.data, indent=2)}
Created at: {record.created_at.isoformat()}
Updated at: {record.updated_at.isoformat()}"""

    async def _update(
        self,
        app: MicroAppModel,
        record_id: str | None,
        data: dict[str, Any] | None,
        partial: bool,
        user_id: str,
    ) -> str:
        """Update an existing record"""
        if not record_id:
            raise ValueError("'record_id' parameter is required for update operation")
        if not data or not isinstance(data, dict):
            msg = "'data' parameter (dict) is required for update operation"
            raise ValueError(msg)

        record_uuid = UUID(record_id)
        updated = await MicroAppDataModel.update(
            record_id=record_uuid,
            user_id=user_id,
            data=data,
            partial=partial,
        )

        if not updated:
            return (
                f"Record {record_id} not found in '{app.name}' or "
                "you don't have permission to update it"
            )

        update_type = "partially updated" if partial else "replaced"
        return f"""Successfully {update_type} record {record_id} in '{app.name}':
New data: {json.dumps(updated.data, indent=2)}
Updated at: {updated.updated_at.isoformat()}"""

    async def _delete(
        self, app: MicroAppModel, record_id: str | None, user_id: str
    ) -> str:
        """Delete a record"""
        if not record_id:
            raise ValueError("'record_id' parameter is required for delete operation")

        record_uuid = UUID(record_id)
        deleted = await MicroAppDataModel.delete(record_uuid, user_id)

        if not deleted:
            return (
                f"Record {record_id} not found in '{app.name}' or "
                "you don't have permission to delete it"
            )

        return f"Successfully deleted record {record_id} from '{app.name}'"

    async def _count(
        self, app: MicroAppModel, filters: dict[str, Any] | None, user_id: str
    ) -> str:
        """Count records"""
        count = await MicroAppDataModel.count(
            app_id=app.id,
            user_id=user_id,
            filters=filters,
        )

        filter_str = f" matching filters {filters}" if filters else ""
        return f"Total records in '{app.name}'{filter_str}: {count}"

    async def _bulk_create(
        self, app: MicroAppModel, data: list[dict[str, Any]] | None, user_id: str
    ) -> str:
        """Create multiple records at once"""
        if not data or not isinstance(data, list):
            msg = (
                "'data' parameter (list of dicts) is required for "
                "bulk_create operation"
            )
            raise ValueError(msg)

        records = await MicroAppDataModel.bulk_create(
            app_id=app.id,
            user_id=user_id,
            data_list=data,
        )

        record_ids = [str(r.id) for r in records]
        return f"""Successfully created {len(records)} records in '{app.name}':
IDs: {", ".join(record_ids)}"""
