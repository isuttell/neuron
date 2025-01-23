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


class MediaListAddItemToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to add to")
    media_item_id: UUID = Field(description="ID of the media item to add")


class MediaListAddItemTool(BaseTool):
    name: str = "media_list_add_item"
    description: str = (
        """This tool adds a media item to a specified media list. The user must have access to the media list."""
    )

    args_schema: Type[MediaListAddItemToolArgs] = MediaListAddItemToolArgs

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

            # Get the current highest index
            max_index = await MediaListModel.get_max_index(list_id) or -1
            new_index = max_index + 1

            # Add the item
            await MediaListModel.add_media_item(list_id, media_item_id, new_index)

            logger.debug(
                f"Added media item {media_item_id} to list {list_id} at index {new_index}"
            )
            return f"Successfully added media item to {media_list.name}"

        except Exception as e:
            logger.error(f"Failed to add media item: {e}", exc_info=True)
            raise
