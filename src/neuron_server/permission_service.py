"""Permission service for checking user access to threads and personalities."""

import asyncio
import time
from uuid import UUID

from neuron_server.logger import logger
from neuron_server.models.personality_user_model import PersonalityUserModel
from neuron_server.models.thread_user_model import ThreadUserModel


class PermissionCache:
    """Simple in-memory cache for permission checks."""

    def __init__(self, ttl_seconds: int = 300) -> None:  # 5 minutes default
        self._cache: dict[str, tuple[bool, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> bool | None:
        """Get cached permission result."""
        if key not in self._cache:
            return None

        result, timestamp = self._cache[key]
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None

        return result

    def set(self, key: str, value: bool) -> None:
        """Cache permission result."""
        self._cache[key] = (value, time.time())

    def invalidate_user(self, user_id: str) -> None:
        """Invalidate all cache entries for a user."""
        keys_to_remove = [key for key in self._cache if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


class PermissionService:
    """Service for checking user permissions on threads and personalities."""

    def __init__(self) -> None:
        self._cache = PermissionCache()
        self._lock = asyncio.Lock()

    async def user_has_thread_access(self, user_id: str, thread_id: UUID) -> bool:
        """Check if user has access to a thread."""
        cache_key = f"{user_id}:thread:{thread_id}"

        # Check cache first
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Query database
        try:
            thread_user = await ThreadUserModel.get(thread_id, user_id)
            has_access = thread_user is not None

            # Cache the result
            self._cache.set(cache_key, has_access)
            return has_access

        except Exception as e:
            logger.error(f"Error checking thread access for user {user_id}: {e}")
            return False

    async def user_has_personality_access(
        self, user_id: str, personality_id: UUID
    ) -> bool:
        """Check if user has access to a personality."""
        cache_key = f"{user_id}:personality:{personality_id}"

        # Check cache first
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Query database
        try:
            personality_user = await PersonalityUserModel.get(personality_id, user_id)
            has_access = personality_user is not None

            # Cache the result
            self._cache.set(cache_key, has_access)
            return has_access

        except Exception as e:
            logger.error(f"Error checking personality access for user {user_id}: {e}")
            return False

    async def get_users_with_thread_access(self, thread_id: UUID) -> list[str]:
        """Get all user IDs that have access to a thread."""
        try:
            thread_users = await ThreadUserModel.get_thread_users(thread_id)
            return [thread_user.user_id for thread_user in thread_users]
        except Exception as e:
            logger.error(f"Error getting thread users for thread {thread_id}: {e}")
            return []

    async def get_users_with_personality_access(
        self, personality_id: UUID
    ) -> list[str]:
        """Get all user IDs that have access to a personality."""
        try:
            personality_users = await PersonalityUserModel.get_personality_users(
                personality_id
            )
            return [personality_user.user_id for personality_user in personality_users]
        except Exception as e:
            logger.error(
                f"Error getting personality users for personality {personality_id}: {e}"
            )
            return []

    async def get_users_with_thread_access_bulk(
        self, thread_ids: list[UUID]
    ) -> dict[UUID, list[str]]:
        """Get users with access to multiple threads in a single query."""
        if not thread_ids:
            return {}

        try:
            thread_users = await ThreadUserModel.get_bulk_thread_users(thread_ids)

            # Group by thread_id
            result: dict[UUID, list[str]] = {thread_id: [] for thread_id in thread_ids}
            for thread_user in thread_users:
                result[thread_user.thread_id].append(thread_user.user_id)

            return result
        except Exception as e:
            logger.error(f"Error getting bulk thread users: {e}")
            return {thread_id: [] for thread_id in thread_ids}

    async def filter_accessible_threads(
        self, user_id: str, thread_ids: list[UUID]
    ) -> list[UUID]:
        """Filter thread IDs to only those the user has access to."""
        if not thread_ids:
            return []

        accessible_threads = []
        for thread_id in thread_ids:
            if await self.user_has_thread_access(user_id, thread_id):
                accessible_threads.append(thread_id)

        return accessible_threads

    async def filter_accessible_personalities(
        self, user_id: str, personality_ids: list[UUID]
    ) -> list[UUID]:
        """Filter personality IDs to only those the user has access to."""
        if not personality_ids:
            return []

        accessible_personalities = []
        for personality_id in personality_ids:
            if await self.user_has_personality_access(user_id, personality_id):
                accessible_personalities.append(personality_id)

        return accessible_personalities

    def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate cache for a specific user."""
        self._cache.invalidate_user(user_id)

    def clear_cache(self) -> None:
        """Clear all cached permissions."""
        self._cache.clear()


# Global permission service instance
permission_service = PermissionService()
