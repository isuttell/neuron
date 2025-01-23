from langchain.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
import asyncio
from neuron_server.pubsub import pubsub
import logging
from uuid import UUID
from langchain_core.runnables import RunnableConfig
from neuron_server.models.media_list_model import MediaListModel

logger = logging.getLogger(__name__)


class MediaListUpdateToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to update")
    name: str = Field(description="New name for the media list")
    description: str = Field(description="New description for the media list")
    tags: List[str] = Field(description="Updated tags for categorization")
    visibility: str = Field(description="Updated visibility setting")
    shared_with: List[str] = Field(description="Updated list of users to share with")


class MediaListUpdateTool(BaseTool):
    name: str = "media_list_update"
    description: str = (
        """This tool updates an existing media list. The user must be the owner of the list."""
    )

    args_schema: Type[MediaListUpdateToolArgs] = MediaListUpdateToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        list_id: UUID,
        name: str,
        description: str,
        tags: List[str],
        visibility: str,
        shared_with: List[str],
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
                f"Updated media list: {updated_list.name} (ID: {updated_list.id})"
            )
            return f"Successfully updated media list '{updated_list.name}'"

        except Exception as e:
            logger.error(f"Failed to update media list: {e}", exc_info=True)
            raise
