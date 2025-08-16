from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from quart import Blueprint, request
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from neuron_server.controllers.auth import TokenPayload, requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.models.micro_app_data_model import MicroAppDataModel
from neuron_server.models.micro_app_model import (
    CreateMicroAppData,
    MicroAppActionModel,
    MicroAppModel,
)

blueprint = Blueprint("micro_app", __name__)


class CreateMicroAppRequest(BaseModel):
    name: str = Field(description="Name of the micro-app")
    description: str = Field(description="Description of the micro-app's purpose")
    schema: dict = Field(description="JSON schema for data validation")
    display_schema: dict | None = Field(
        default=None, description="Display configuration for frontend rendering"
    )
    actions: list[MicroAppActionModel] = Field(
        default_factory=list, description="Available actions for this app"
    )


class UpdateMicroAppRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    display_schema: dict | None = None


class CreateMicroAppDataRequest(BaseModel):
    data: dict[str, Any] = Field(description="Data conforming to the app's schema")


class UpdateMicroAppDataRequest(BaseModel):
    data: dict[str, Any] = Field(description="Updated data")
    partial: bool = Field(
        default=False, description="Whether to perform partial update"
    )


@blueprint.get("/micro-apps")
@requires_auth
async def list_micro_apps() -> list[dict]:
    """List all micro-apps available to the user"""
    assert isinstance(request.token, TokenPayload)

    apps = await MicroAppModel.list_all()
    return [app.model_dump(mode="json") for app in apps]


@blueprint.post("/micro-apps")
@requires_auth
@requires_csrf
async def create_micro_app() -> dict:
    """Create a new micro-app"""
    assert isinstance(request.token, TokenPayload)

    try:
        data = await request.get_json()
        if not data:
            raise BadRequest("Request body is required")

        create_request = CreateMicroAppRequest.model_validate(data)

        app = await MicroAppModel.create(
            CreateMicroAppData(
                name=create_request.name,
                description=create_request.description,
                schema=create_request.schema,
                display_schema=create_request.display_schema,
                creator_id=request.token.user_id,
                actions=create_request.actions,
            )
        )

        return app.model_dump(mode="json")

    except Exception as e:
        raise BadRequest(f"Failed to create micro-app: {str(e)}") from e


@blueprint.get("/micro-apps/<uuid:app_id>")
@requires_auth
async def get_micro_app(app_id: UUID) -> dict:
    """Get a specific micro-app by ID"""
    assert isinstance(request.token, TokenPayload)

    app = await MicroAppModel.get(app_id)
    if not app:
        raise NotFound("Micro-app not found")

    return app.model_dump(mode="json")


@blueprint.put("/micro-apps/<uuid:app_id>")
@requires_auth
@requires_csrf
async def update_micro_app(app_id: UUID) -> dict:
    """Update a micro-app (name, description, display_schema only)"""
    assert isinstance(request.token, TokenPayload)

    try:
        data = await request.get_json()
        if not data:
            raise BadRequest("Request body is required")

        update_request = UpdateMicroAppRequest.model_validate(data)

        # Get the app to check ownership
        app = await MicroAppModel.get(app_id)
        if not app:
            raise NotFound("Micro-app not found")

        if app.creator_id != request.token.user_id:
            raise Forbidden("You can only update micro-apps you created")

        # Prepare updates dict
        updates = {}
        if update_request.name is not None:
            updates["name"] = update_request.name
        if update_request.description is not None:
            updates["description"] = update_request.description
        if update_request.display_schema is not None:
            updates["display_schema"] = update_request.display_schema

        success = await MicroAppModel.update(app_id, updates)
        if not success:
            raise BadRequest("Failed to update micro-app")

        # Return updated app
        updated_app = await MicroAppModel.get(app_id)
        return updated_app.model_dump(mode="json")

    except Exception as e:
        if isinstance(e, (BadRequest, NotFound, Forbidden)):
            raise
        raise BadRequest(f"Failed to update micro-app: {str(e)}") from e


@blueprint.delete("/micro-apps/<uuid:app_id>")
@requires_auth
@requires_csrf
async def delete_micro_app(app_id: UUID) -> dict:
    """Delete a micro-app and all its data"""
    assert isinstance(request.token, TokenPayload)

    # Get the app to check ownership
    app = await MicroAppModel.get(app_id)
    if not app:
        raise NotFound("Micro-app not found")

    if app.creator_id != request.token.user_id:
        raise Forbidden("You can only delete micro-apps you created")

    success = await MicroAppModel.delete(app_id)
    if not success:
        raise BadRequest("Failed to delete micro-app")

    return {"message": "Micro-app deleted successfully"}


@blueprint.get("/micro-apps/<uuid:app_id>/data")
@requires_auth
async def list_micro_app_data(app_id: UUID) -> dict:
    """List data records for a micro-app"""
    assert isinstance(request.token, TokenPayload)

    # Check if app exists
    app = await MicroAppModel.get(app_id)
    if not app:
        raise NotFound("Micro-app not found")

    # Get query parameters
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    # Parse filters from query parameters
    filters = {}
    for key, value in request.args.items():
        if key not in ["limit", "offset"]:
            filters[key] = value

    # Get data records
    records = await MicroAppDataModel.query(
        app_id=app_id,
        user_id=request.token.user_id,
        filters=filters if filters else None,
        limit=limit,
        offset=offset,
    )

    # Get total count
    total = await MicroAppDataModel.count(
        app_id=app_id,
        user_id=request.token.user_id,
        filters=filters if filters else None,
    )

    return {
        "records": [record.model_dump(mode="json") for record in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@blueprint.post("/micro-apps/<uuid:app_id>/data")
@requires_auth
@requires_csrf
async def create_micro_app_data(app_id: UUID) -> dict:
    """Create a new data record for a micro-app"""
    assert isinstance(request.token, TokenPayload)

    try:
        data = await request.get_json()
        if not data:
            raise BadRequest("Request body is required")

        create_request = CreateMicroAppDataRequest.model_validate(data)

        record = await MicroAppDataModel.create(
            app_id=app_id,
            user_id=request.token.user_id,
            data=create_request.data,
        )

        return record.model_dump(mode="json")

    except Exception as e:
        raise BadRequest(f"Failed to create data record: {str(e)}") from e


@blueprint.get("/micro-apps/<uuid:app_id>/data/<uuid:record_id>")
@requires_auth
async def get_micro_app_data(app_id: UUID, record_id: UUID) -> dict:
    """Get a specific data record"""
    assert isinstance(request.token, TokenPayload)

    record = await MicroAppDataModel.get(record_id, request.token.user_id)
    if not record or record.app_id != app_id:
        raise NotFound("Data record not found")

    return record.model_dump(mode="json")


@blueprint.put("/micro-apps/<uuid:app_id>/data/<uuid:record_id>")
@requires_auth
@requires_csrf
async def update_micro_app_data(app_id: UUID, record_id: UUID) -> dict:
    """Update a data record"""
    assert isinstance(request.token, TokenPayload)

    try:
        data = await request.get_json()
        if not data:
            raise BadRequest("Request body is required")

        update_request = UpdateMicroAppDataRequest.model_validate(data)

        record = await MicroAppDataModel.update(
            record_id=record_id,
            user_id=request.token.user_id,
            data=update_request.data,
            partial=update_request.partial,
        )

        if not record or record.app_id != app_id:
            raise NotFound("Data record not found")

        return record.model_dump(mode="json")

    except Exception as e:
        if isinstance(e, NotFound):
            raise
        raise BadRequest(f"Failed to update data record: {str(e)}") from e


@blueprint.delete("/micro-apps/<uuid:app_id>/data/<uuid:record_id>")
@requires_auth
@requires_csrf
async def delete_micro_app_data(app_id: UUID, record_id: UUID) -> dict:
    """Delete a data record"""
    assert isinstance(request.token, TokenPayload)

    success = await MicroAppDataModel.delete(record_id, request.token.user_id)
    if not success:
        raise NotFound("Data record not found")

    return {"message": "Data record deleted successfully"}
