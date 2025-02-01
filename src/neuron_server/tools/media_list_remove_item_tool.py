import asyncio
import logging
from typing import Any
from uuid import UUID

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.media_list_item_model import MediaListItemModel
from neuron_server.models.media_list_model import MediaListModel

logger = logging.getLogger(__name__)


class MediaListRemoveItemToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to remove from")
    media_item_id: UUID = Field(description="ID of the media item to remove")


class MediaListRemoveItemTool(BaseTool):
    name: str = "media_list_remove_item"
    description: str = (
        "This tool removes a media item from a specified media list. "
        "The user must have access to the media list."
    )

    args_schema: type[MediaListRemoveItemToolArgs] = MediaListRemoveItemToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self, list_id: UUID, media_item_id: UUID, config: RunnableConfig
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            # Verify user has access to the list
            media_list = await MediaListModel.get(list_id)
            if not media_list:
                raise ValueError(f"Media list {list_id} not found")

            if media_list.user_id != user_id and user_id not in media_list.shared_with:
                raise ValueError("You do not have access to this media list")

            # Find the item in the list
            items = await MediaListItemModel.get_by_list(list_id)
            target_item = next(
                (item for item in items if item.media_item_id == media_item_id), None
            )

            if not target_item:
                return f"Item not found in media list '{media_list.name}'"

            # Remove the item
            await MediaListItemModel.delete(target_item.id)

            logger.debug(
                "Removed media item %s from list %s",
                media_item_id,
                list_id,
            )
            return f"Successfully removed media item from {media_list.name}"

        except Exception as e:
            logger.error("Failed to remove media item: %s", str(e), exc_info=True)
            raise
