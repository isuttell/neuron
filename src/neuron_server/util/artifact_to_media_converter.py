"""Utility to convert tool artifacts to MediaItem database records.

This module provides functionality to create MediaItemModel records from tool artifacts
when thread context is available, enabling tools to be thread-agnostic while still
supporting media persistence when appropriate.
"""

from uuid import UUID

from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.tools.artifact_types import ToolMediaArtifact


async def create_media_items_from_artifacts(
    artifacts: list[dict],
    thread_id: UUID | None = None,
    user_id: str | None = None,
) -> None:
    """Create MediaItem records from tool artifacts.

    Args:
        artifacts: List of artifact dictionaries from tool responses
        thread_id: Thread ID to associate with media items (optional)
        user_id: User ID to associate with media items (optional)

    Note:
        This function only processes media artifacts. Other artifact types are ignored.
        If thread_id is None, no media items will be created.
        The artifacts already contain real UUIDs that will be used as the
        media_item IDs.
    """
    if not thread_id:
        logger.debug("No thread_id provided, skipping media item creation")
        return

    for artifact_dict in artifacts:
        # Only process media artifacts
        if artifact_dict.get("type") != "media":
            continue

        try:
            # Parse the artifact using Pydantic model for validation
            artifact = ToolMediaArtifact.model_validate(artifact_dict)

            for item in artifact.items:
                # Create MediaItem record with the predefined UUID from artifact
                create_params = MediaItemModel.CreateParams(
                    media_id=item.id,
                    thread_id=thread_id,
                    user_id=user_id,
                    url=item.url,
                    media_type=artifact.media_type,
                    name=item.caption,
                    description=item.description,
                )

                media_item = await MediaItemModel.create(params=create_params)

                logger.debug(
                    f"Created media_item {media_item.id} from artifact "
                    f"({artifact.media_type}: {item.url})"
                )

        except Exception as e:
            logger.error(
                f"Failed to create media item from artifact: {e}", exc_info=True
            )
            continue
