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


class MediaListReadToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to read")


class MediaListReadTool(BaseTool):
    name: str = "media_list_read"
    description: str = (
        """This tool retrieves details about a specific media list. The user must have access to the list."""
    )

    args_schema: Type[MediaListReadToolArgs] = MediaListReadToolArgs

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

            # Verify access
            if media_list.user_id != user_id and user_id not in media_list.shared_with:
                raise ValueError("You do not have access to this media list")

            # Format the response
            response = f"Media List: {media_list.name}\n"
            response += f"ID: {media_list.id}\n"
            response += f"Description: {media_list.description}\n"
            response += f"Owner: {media_list.user_id}\n"
            response += f"Visibility: {media_list.visibility}\n"
            if media_list.tags:
                response += f"Tags: {', '.join(media_list.tags)}\n"
            if media_list.shared_with:
                response += f"Shared with: {', '.join(media_list.shared_with)}\n"
            response += f"Created: {media_list.created_at}\n"
            response += f"Last Updated: {media_list.updated_at}\n"

            logger.debug(
                f"Retrieved media list: {media_list.name} (ID: {media_list.id})"
            )
            return response

        except Exception as e:
            logger.error(f"Failed to read media list: {e}", exc_info=True)
            raise
