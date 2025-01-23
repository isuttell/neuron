from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import asyncio
from neuron_server.pubsub import pubsub
import logging
from uuid import UUID
from langchain_core.runnables import RunnableConfig
from neuron_server.models.media_list_model import MediaListModel
from neuron_server.models.media_list_item_model import MediaListItemModel

logger = logging.getLogger(__name__)


class MediaListRemoveItemToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to remove from")
    media_item_id: UUID = Field(description="ID of the media item to remove")


class MediaListRemoveItemTool(BaseTool):
    name: str = "media_list_remove_item"
    description: str = (
        """This tool removes a media item from a specified media list. The user must have access to the media list."""
    )

    args_schema: Type[MediaListRemoveItemToolArgs] = MediaListRemoveItemToolArgs

    def _run(self, *args, **kwargs) -> str:
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

            logger.debug(f"Removed media item {media_item_id} from list {list_id}")
            return f"Successfully removed media item from {media_list.name}"

        except Exception as e:
            logger.error(f"Failed to remove media item: {e}", exc_info=True)
            raise
