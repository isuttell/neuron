import asyncio
import logging

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from neuron_server.models.media_list_model import MediaListModel

logger = logging.getLogger(__name__)


class MediaListAccessToolArgs(BaseModel):
    pass  # No additional args needed - uses user_id from config


class MediaListAccessTool(BaseTool):
    name: str = "media_list_access"
    description: str = (
        """This tool returns a list of all media lists that the user has access to (either owns or shared with them)."""
    )

    args_schema: type[MediaListAccessToolArgs] = MediaListAccessToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, config: RunnableConfig) -> str:
        try:
            user_id = config["configurable"].get("user_id")
            if not user_id:
                raise ValueError("User ID is required")

            media_lists = await MediaListModel.list_for_user(user_id)

            # Format the response
            if not media_lists:
                return "No media lists found"

            response = "Available media lists:\n"
            for list_item in media_lists:
                response += f"- {list_item.name} (ID: {list_item.id})\n"
                if list_item.description:
                    response += f"  Description: {list_item.description}\n"

            logger.debug(f"Retrieved {len(media_lists)} media lists for user {user_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to retrieve media lists: {e}", exc_info=True)
            raise
