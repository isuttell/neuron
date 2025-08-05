"""Utility for fetching build information from client container."""

import asyncio
import logging
import time
from typing import Optional

import aiohttp

from neuron_server.config import config

logger = logging.getLogger(__name__)

# Constants
PING_INTERVAL_SECONDS = 30  # WebSocket ping frequency
BUILD_INFO_CACHE_SECONDS = 30  # Align cache with ping frequency
BUILD_INFO_FETCH_TIMEOUT_SECONDS = 5  # HTTP request timeout


class BuildInfoManager:
    """Manages fetching and caching of build information from client container."""

    def __init__(self) -> None:
        self.current_hash: Optional[str] = None
        self.git_commit: Optional[str] = None
        self.last_check: float = 0
        self.check_interval: float = BUILD_INFO_CACHE_SECONDS

    async def get_current_hash(self) -> Optional[str]:
        """Get the current asset hash, fetching if needed."""

        current_time = time.time()

        # Fetch if we don't have a hash or it's time to check again
        if (
            self.current_hash is None
            or (current_time - self.last_check) > self.check_interval
        ):
            await self._fetch_build_info()
            self.last_check = current_time

        return self.current_hash

    async def get_git_commit(self) -> Optional[str]:
        """Get the current git commit, fetching if needed."""
        current_time = time.time()

        # Fetch if we don't have a commit or it's time to check again
        if (
            self.git_commit is None
            or (current_time - self.last_check) > self.check_interval
        ):
            await self._fetch_build_info()
            self.last_check = current_time

        # Fallback to server's git commit if client doesn't have one
        if self.git_commit is None:
            from neuron_server.config import config

            return config.git_commit

        return self.git_commit

    async def _fetch_build_info(self) -> None:
        """Fetch build info from client container."""
        try:
            # Try to determine client URL based on environment
            client_url = self._get_client_url()
            if not client_url:
                return

            build_info_url = f"{client_url}/build-info.json"

            timeout = aiohttp.ClientTimeout(total=BUILD_INFO_FETCH_TIMEOUT_SECONDS)
            async with (
                aiohttp.ClientSession() as session,
                session.get(build_info_url, timeout=timeout) as response,
            ):
                http_ok = 200
                if response.status == http_ok:
                    data = await response.json()
                    self.current_hash = data.get("assetHash")
                    self.git_commit = data.get("gitCommit")
                    logger.debug(
                        f"Fetched build info: {self.current_hash}, "
                        f"commit: {self.git_commit}"
                    )
                else:
                    logger.warning(
                        f"Failed to fetch build info: HTTP {response.status}"
                    )

        except asyncio.TimeoutError:
            logger.warning("Timeout fetching build info from client")
        except Exception as e:
            logger.warning(f"Error fetching build info: {e}")

    def _get_client_url(self) -> Optional[str]:
        """Determine the client container URL based on configuration."""
        # In development mode with SERVE_CLIENT=true, no separate client container
        if config.serve_client:
            return ""

        # Use configured client URL
        return config.client_url


# Global instance
build_info_manager = BuildInfoManager()
