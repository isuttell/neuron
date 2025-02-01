import asyncio
import logging
from typing import Any
from uuid import UUID

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.media_list_model import MediaListModel

logger = logging.getLogger(__name__)


class MediaListUpdateToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to update")
    name: str = Field(description="New name for the media list")
    description: str = Field(description="New description for the media list")
    tags: list[str] = Field(description="Updated tags for categorization")
    visibility: str = Field(description="Updated visibility setting")
    shared_with: list[str] = Field(description="Updated list of users to share with")


class MediaListUpdateTool(BaseTool):
    name: str = "media_list_update"
    description: str = (
        "This tool updates an existing media list. "
        "The user must be the owner of the list."
    )

    args_schema: type[MediaListUpdateToolArgs] = MediaListUpdateToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0913
        self,
        list_id: UUID,
        name: str,
        description: str,
        tags: list[str],
        visibility: str,
        shared_with: list[str],
        config: RunnableConfig,
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            # Get the media list
            media_list = await MediaListModel.get(list_id)
            if not media_list:
                raise ValueError(f"Media list {list_id} not found")

            # Verify ownership (only owner can update)
            if media_list.user_id != user_id:
                raise ValueError("You must be the owner to update this media list")

            # Update the media list
            updated_list = await MediaListModel.update(
                id=list_id,
                name=name,
                description=description,
                tags=tags,
                visibility=visibility,
                shared_with=shared_with,
            )

            logger.debug(
                "Updated media list: %s (ID: %s)",
                updated_list.name,
                updated_list.id,
            )
            return f"Successfully updated media list '{updated_list.name}'"

        except Exception as e:
            logger.error("Failed to update media list: %s", str(e), exc_info=True)
            raise
