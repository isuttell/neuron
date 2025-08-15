from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID, uuid4

import jsonschema
from pydantic import BaseModel, Field
from sqlalchemy import Float, and_, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import ColumnElement
from sqlalchemy.sql.functions import Function
from sqlalchemy.sql.selectable import Select

from neuron_server.database import MicroApp, MicroAppData, get_session


class MicroAppDataModel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    app_id: UUID = Field(description="ID of the micro-app this data belongs to")
    user_id: str = Field(description="ID of the user who owns this data")
    data: dict[str, Any] = Field(
        description="The actual data conforming to the app's schema"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @staticmethod
    async def validate_against_schema(data: dict, schema: dict) -> None:
        """Validate data against the app's JSON schema"""
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Data validation failed: {e.message}") from e

    @classmethod
    async def create(cls, app_id: UUID, user_id: str, data: dict[str, Any]) -> Self:
        """Create a new data record for a micro-app"""
        async with get_session() as session:
            # Get the app to validate against its schema
            app = await session.get(MicroApp, app_id)
            if not app:
                raise ValueError(f"App with ID {app_id} not found")

            # Validate the data
            await cls.validate_against_schema(data, app.schema)

            # Create the data record
            record = MicroAppData(
                app_id=app_id,
                user_id=user_id,
                data=data,
            )
            session.add(record)
            await session.commit()

            return cls(
                id=record.id,
                app_id=record.app_id,
                user_id=record.user_id,
                data=record.data,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

    @classmethod
    async def get(cls, record_id: UUID, user_id: str) -> Self | None:
        """Get a specific data record (only if owned by the user)"""
        async with get_session() as session:
            result = await session.execute(
                select(MicroAppData).where(
                    and_(
                        MicroAppData.id == record_id,
                        MicroAppData.user_id == user_id,
                    )
                )
            )
            record = result.scalar_one_or_none()

            if not record:
                return None

            return cls(
                id=record.id,
                app_id=record.app_id,
                user_id=record.user_id,
                data=record.data,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

    @classmethod
    async def query(
        cls,
        app_id: UUID,
        user_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Self]:
        """Query data records for a micro-app (user-segmented)"""
        async with get_session() as session:
            query = select(MicroAppData).where(
                and_(
                    MicroAppData.app_id == app_id,
                    MicroAppData.user_id == user_id,
                )
            )

            # Apply filters using safe JSONB operations
            if filters:
                for key, value in filters.items():
                    # Support nested key access with dot notation
                    keys = key.split(".")
                    # Validate key components to prevent injection
                    for k in keys:
                        if not k.replace("_", "").replace("-", "").isalnum():
                            raise ValueError(f"Invalid key component: {k}")

                    # Use PostgreSQL's jsonb_extract_path_text with array of keys
                    path_expr = func.jsonb_extract_path_text(MicroAppData.data, *keys)
                    query = query.where(path_expr == str(value))

            query = query.limit(limit).offset(offset)
            result = await session.execute(query)
            records = result.scalars().all()

            return [
                cls(
                    id=record.id,
                    app_id=record.app_id,
                    user_id=record.user_id,
                    data=record.data,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
                for record in records
            ]

    @classmethod
    async def update(
        cls,
        record_id: UUID,
        user_id: str,
        data: dict[str, Any],
        partial: bool = False,
    ) -> Self | None:
        """Update a data record (only if owned by the user)"""
        async with get_session() as session:
            record = await session.execute(
                select(MicroAppData).where(
                    and_(
                        MicroAppData.id == record_id,
                        MicroAppData.user_id == user_id,
                    )
                )
            )
            record = record.scalar_one_or_none()

            if not record:
                return None

            # Get the app to validate against its schema
            app = await session.get(MicroApp, record.app_id)
            if not app:
                raise ValueError(f"App with ID {record.app_id} not found")

            # Merge with existing data if partial update
            new_data = {**record.data, **data} if partial else data

            # Validate the new data
            await cls.validate_against_schema(new_data, app.schema)

            # Update the record
            record.data = new_data
            await session.commit()
            await session.refresh(record)

            return cls(
                id=record.id,
                app_id=record.app_id,
                user_id=record.user_id,
                data=record.data,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

    @classmethod
    async def delete(cls, record_id: UUID, user_id: str) -> bool:
        """Delete a data record (only if owned by the user)"""
        async with get_session() as session:
            result = await session.execute(
                select(MicroAppData).where(
                    and_(
                        MicroAppData.id == record_id,
                        MicroAppData.user_id == user_id,
                    )
                )
            )
            record = result.scalar_one_or_none()

            if not record:
                return False

            await session.delete(record)
            await session.commit()
            return True

    @classmethod
    async def count(
        cls,
        app_id: UUID,
        user_id: str,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count data records for a micro-app (user-segmented)"""
        async with get_session() as session:
            query = select(func.count(MicroAppData.id)).where(
                and_(
                    MicroAppData.app_id == app_id,
                    MicroAppData.user_id == user_id,
                )
            )

            # Apply filters using safe JSONB operations
            if filters:
                for key, value in filters.items():
                    keys = key.split(".")
                    # Validate key components to prevent injection
                    for k in keys:
                        if not k.replace("_", "").replace("-", "").isalnum():
                            raise ValueError(f"Invalid key component: {k}")

                    # Use PostgreSQL's jsonb_extract_path_text with array of keys
                    path_expr = func.jsonb_extract_path_text(MicroAppData.data, *keys)
                    query = query.where(path_expr == str(value))

            result = await session.execute(query)
            return result.scalar() or 0

    @classmethod
    async def aggregate(
        cls,
        app_id: UUID,
        user_id: str,
        field: str,
        operation: str,
        filters: dict[str, Any] | None = None,
    ) -> float | int | None:
        """Perform aggregation operations on data records"""
        async with get_session() as session:
            # Build the base query using safe JSON path extraction
            keys = field.split(".")
            # Validate key components to prevent injection
            for k in keys:
                if not k.replace("_", "").replace("-", "").isalnum():
                    raise ValueError(f"Invalid key component: {k}")

            json_path = func.jsonb_extract_path(MicroAppData.data, *keys)

            # Select the appropriate aggregation function
            if operation == "sum":
                agg_func = func.sum(json_path.cast(JSONB).cast(Float))
            elif operation == "avg":
                agg_func = func.avg(json_path.cast(JSONB).cast(Float))
            elif operation == "min":
                agg_func = func.min(json_path.cast(JSONB))
            elif operation == "max":
                agg_func = func.max(json_path.cast(JSONB))
            elif operation == "count":
                agg_func = func.count(json_path)
            else:
                raise ValueError(f"Unsupported aggregation operation: {operation}")

            query = select(agg_func).where(
                and_(
                    MicroAppData.app_id == app_id,
                    MicroAppData.user_id == user_id,
                )
            )

            # Apply filters using safe JSONB operations
            if filters:
                for key, value in filters.items():
                    filter_keys = key.split(".")
                    # Validate key components to prevent injection
                    for k in filter_keys:
                        if not k.replace("_", "").replace("-", "").isalnum():
                            raise ValueError(f"Invalid key component: {k}")

                    # Use PostgreSQL's jsonb_extract_path_text with array of keys
                    filter_expr = func.jsonb_extract_path_text(
                        MicroAppData.data, *filter_keys
                    )
                    query = query.where(filter_expr == str(value))

            result = await session.execute(query)
            return result.scalar()

    @classmethod
    async def bulk_create(
        cls, app_id: UUID, user_id: str, data_list: list[dict[str, Any]]
    ) -> Sequence[Self]:
        """Create multiple data records at once"""
        async with get_session() as session:
            # Get the app to validate against its schema
            app = await session.get(MicroApp, app_id)
            if not app:
                raise ValueError(f"App with ID {app_id} not found")

            # Validate all data
            for data in data_list:
                await cls.validate_against_schema(data, app.schema)

            # Create all records
            records = []
            for data in data_list:
                record = MicroAppData(
                    app_id=app_id,
                    user_id=user_id,
                    data=data,
                )
                session.add(record)
                records.append(record)

            await session.commit()

            return [
                cls(
                    id=record.id,
                    app_id=record.app_id,
                    user_id=record.user_id,
                    data=record.data,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
                for record in records
            ]

    @classmethod
    async def admin_query(
        cls,
        app_id: UUID,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Self]:
        """Query data records for a micro-app across ALL users (admin only)"""
        async with get_session() as session:
            query = select(MicroAppData).where(MicroAppData.app_id == app_id)

            if filters:
                for key, value in filters.items():
                    if key == "user_id":
                        query = query.where(MicroAppData.user_id == str(value))
                        continue

                    keys = key.split(".")
                    for k in keys:
                        if not k.replace("_", "").replace("-", "").isalnum():
                            raise ValueError(f"Invalid key component: {k}")

                    path_expr = func.jsonb_extract_path_text(MicroAppData.data, *keys)
                    query = query.where(path_expr == str(value))

            query = (
                query.limit(limit)
                .offset(offset)
                .order_by(MicroAppData.created_at.desc())
            )
            result = await session.execute(query)
            records = result.scalars().all()

            return [
                cls(
                    id=record.id,
                    app_id=record.app_id,
                    user_id=record.user_id,
                    data=record.data,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
                for record in records
            ]

    @classmethod
    async def admin_get(cls, record_id: UUID) -> Self | None:
        """Get a specific data record by ID regardless of user (admin only)"""
        async with get_session() as session:
            result = await session.execute(
                select(MicroAppData).where(MicroAppData.id == record_id)
            )
            record = result.scalar_one_or_none()

            if not record:
                return None

            return cls(
                id=record.id,
                app_id=record.app_id,
                user_id=record.user_id,
                data=record.data,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

    @classmethod
    async def admin_count(
        cls,
        app_id: UUID,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count data records for a micro-app across ALL users (admin only)"""
        async with get_session() as session:
            query = select(func.count(MicroAppData.id)).where(
                MicroAppData.app_id == app_id
            )

            if filters:
                for key, value in filters.items():
                    if key == "user_id":
                        query = query.where(MicroAppData.user_id == str(value))
                        continue

                    keys = key.split(".")
                    for k in keys:
                        if not k.replace("_", "").replace("-", "").isalnum():
                            raise ValueError(f"Invalid key component: {k}")

                    path_expr = func.jsonb_extract_path_text(MicroAppData.data, *keys)
                    query = query.where(path_expr == str(value))

            result = await session.execute(query)
            return result.scalar() or 0

    @classmethod
    async def admin_aggregate(
        cls,
        app_id: UUID,
        field: str,
        operation: str,
        filters: dict[str, Any] | None = None,
    ) -> float | int | None:
        """Perform aggregation operations on data records across ALL users."""
        async with get_session() as session:
            # Validate and build field path
            keys = field.split(".")
            for k in keys:
                if not k.replace("_", "").replace("-", "").isalnum():
                    raise ValueError(f"Invalid key component: {k}")

            json_path = func.jsonb_extract_path(MicroAppData.data, *keys)

            # Get aggregation function
            agg_func = cls._get_aggregation_function(json_path, operation)
            query = select(agg_func).where(MicroAppData.app_id == app_id)

            # Apply filters
            query = cls._apply_admin_filters(query, filters)

            result = await session.execute(query)
            return result.scalar()

    @staticmethod
    def _get_aggregation_function(
        json_path: ColumnElement[Any], operation: str
    ) -> Function[Any]:
        """Get the appropriate SQLAlchemy aggregation function."""
        aggregation_map = {
            "sum": lambda: func.sum(json_path.cast(JSONB).cast(Float)),
            "avg": lambda: func.avg(json_path.cast(JSONB).cast(Float)),
            "min": lambda: func.min(json_path.cast(JSONB)),
            "max": lambda: func.max(json_path.cast(JSONB)),
            "count": lambda: func.count(json_path),
        }

        if operation not in aggregation_map:
            raise ValueError(f"Unsupported aggregation operation: {operation}")

        return aggregation_map[operation]()

    @staticmethod
    def _apply_admin_filters(
        query: Select[tuple[MicroAppData]], filters: dict[str, Any] | None
    ) -> Select[tuple[MicroAppData]]:
        """Apply filters to admin queries (no user_id restrictions)."""
        if not filters:
            return query

        for key, value in filters.items():
            if key == "user_id":
                query = query.where(MicroAppData.user_id == str(value))
                continue

            filter_keys = key.split(".")
            for k in filter_keys:
                if not k.replace("_", "").replace("-", "").isalnum():
                    raise ValueError(f"Invalid key component: {k}")

            filter_expr = func.jsonb_extract_path_text(MicroAppData.data, *filter_keys)
            query = query.where(filter_expr == str(value))

        return query
