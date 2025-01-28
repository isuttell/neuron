import asyncio
import logging

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.media_list_model import MediaListModel

logger = logging.getLogger(__name__)


class MediaListCreateToolArgs(BaseModel):
    name: str = Field(description="Name of the media list")
    description: str = Field(description="Description of the media list")
    tags: list[str] | None = Field(
        default=None, description="Optional tags for categorization"
    )
    visibility: str = Field(
        default="private",
        description="Visibility setting (private/public)",
    )
    shared_with: list[str] | None = Field(
        default=None, description="Optional list of user IDs to share with"
    )


class MediaListCreateTool(BaseTool):
    name: str = "media_list_create"
    description: str = (
        """This tool creates a new media list owned by the current user."""
    )

    args_schema: type[MediaListCreateToolArgs] = MediaListCreateToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        name: str,
        description: str,
        tags: list[str] | None = None,
        visibility: str = "private",
        shared_with: list[str] | None = None,
        config: RunnableConfig = None,
    ) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            # Create the media list
            media_list = await MediaListModel.create(
                name=name,
                description=description,
                user_id=user_id,
                tags=tags,
                visibility=visibility,
                shared_with=shared_with,
            )

            logger.debug(f"Created media list: {media_list.name} (ID: {media_list.id})")
            return f"Successfully created media list '{media_list.name}' (ID: {media_list.id})"

        except Exception as e:
            logger.error(f"Failed to create media list: {e}", exc_info=True)
            raise
