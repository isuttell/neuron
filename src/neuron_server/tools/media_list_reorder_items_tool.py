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


class MediaListReorderItemsToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to reorder items in")
    media_item_ids: list[UUID] = Field(
        description="List of media item IDs in their desired order"
    )


class MediaListReorderItemsTool(BaseTool):
    name: str = "media_list_reorder_items"
    description: str = (
        "This tool reorders items in a media list. The user must be the owner of the list. "  # noqa: E501
        "Provide the list_id and an array of media_item_ids in their desired order."
    )

    args_schema: type[MediaListReorderItemsToolArgs] = MediaListReorderItemsToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self, list_id: UUID, media_item_ids: list[UUID], config: RunnableConfig
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            # Get the media list
            media_list = await MediaListModel.get(list_id)
            if not media_list:
                raise ValueError(f"Media list {list_id} not found")

            # Verify ownership (only owner can reorder)
            if media_list.user_id != user_id:
                raise ValueError(
                    "You must be the owner to reorder items in this media list"
                )

            # Get all current items in the list
            current_items = await MediaListItemModel.get_by_list(list_id)
            if not current_items:
                raise ValueError("No items found in the media list")

            # Create a mapping of media_item_id to MediaListItem
            item_map = {item.media_item_id: item for item in current_items}

            # Verify all provided media_item_ids exist in the list
            for media_item_id in media_item_ids:
                if media_item_id not in item_map:
                    raise ValueError(
                        f"Media item {media_item_id} not found in the list"
                    )

            # Verify we're not missing any items
            if len(media_item_ids) != len(current_items):
                raise ValueError(
                    "Number of items in new order doesn't match current list length"
                )

            # Update indices based on new order
            for index, media_item_id in enumerate(media_item_ids):
                list_item = item_map[media_item_id]
                if list_item.index != index:
                    await MediaListItemModel.update(
                        id=list_item.id,
                        index=index,
                        media_list_id=list_id,
                        media_item_id=media_item_id,
                    )

            logger.debug(
                "Reordered %d items in list %s",
                len(media_item_ids),
                list_id,
            )
            return (
                f"Successfully reordered {len(media_item_ids)} items in "
                f"media list '{media_list.name}'"
            )

        except Exception as e:
            logger.error(
                "Failed to reorder media list items: %s", str(e), exc_info=True
            )
            raise
