from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import asyncio
from neuron_server.pubsub import pubsub
import logging
from uuid import UUID
from langchain_core.runnables import RunnableConfig
from neuron_server.models.media_list_model import MediaListModel

logger = logging.getLogger(__name__)


class MediaListDeleteToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to delete")


class MediaListDeleteTool(BaseTool):
    name: str = "media_list_delete"
    description: str = (
        """This tool deletes a media list. The user must be the owner of the list."""
    )

    args_schema: Type[MediaListDeleteToolArgs] = MediaListDeleteToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, list_id: UUID, config: RunnableConfig) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            # Get the media list
            media_list = await MediaListModel.get(list_id)
            if not media_list:
                raise ValueError(f"Media list {list_id} not found")

            # Verify ownership (only owner can delete)
            if media_list.user_id != user_id:
                raise ValueError("You must be the owner to delete this media list")

            # Store name for response
            list_name = media_list.name

            # Delete the media list
            await MediaListModel.delete(list_id)

            logger.debug(f"Deleted media list: {list_name} (ID: {list_id})")
            return f"Successfully deleted media list '{list_name}'"

        except Exception as e:
            logger.error(f"Failed to delete media list: {e}", exc_info=True)
            raise
