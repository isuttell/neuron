import asyncio
import logging
from uuid import UUID

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.models.media_list_item_model import MediaListItemModel
from neuron_server.models.media_list_model import MediaListModel

logger = logging.getLogger(__name__)


class MediaListGetItemsToolArgs(BaseModel):
    list_id: UUID = Field(description="ID of the media list to get items from")


class MediaListGetItemsTool(BaseTool):
    name: str = "media_list_get_items"
    description: str = (
        """This tool retrieves all items from a specified media list. The user must have access to the media list."""
    )

    args_schema: type[MediaListGetItemsToolArgs] = MediaListGetItemsToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, list_id: UUID, config: RunnableConfig) -> str:
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

            # Get all items in the list
            items = await MediaListItemModel.get_by_list(list_id)

            if not items:
                return f"No items found in media list '{media_list.name}'"

            # Get the full media items
            media_items = await MediaItemModel.get_many(
                [item.media_item_id for item in items]
            )

            # Format the response
            response_parts = []
            for media_item in media_items:
                if media_item.type == "image":
                    response_parts.append(
                        f"""\
<image id="{media_item.id}">
    <display>![{media_item.name}]({media_item.url})</display>
</image>"""
                    )
                elif media_item.type == "video":
                    response_parts.append(
                        f"""\
<video id="{media_item.id}">
    <display><video src="{media_item.url}"></video></display>
</video>"""
                    )
                elif media_item.type == "audio":
                    response_parts.append(
                        f"""\
<audio id="{media_item.id}">
    <display><audio src="{media_item.url}"></audio></display>
</audio>"""
                    )

            logger.debug(f"Retrieved {len(items)} items from list {list_id}")
            return f"""\
<media_list id="{media_list.id}" name="{media_list.name}">
{chr(10).join(response_parts)}
</media_list>"""

        except Exception as e:
            logger.error(f"Failed to retrieve media list items: {e}", exc_info=True)
            raise
