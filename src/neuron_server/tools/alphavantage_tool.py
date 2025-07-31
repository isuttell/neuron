import asyncio
import json
import re
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.cache import client as redis_client
from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.tools.artifact_types import (
    ToolArtifactMetadata,
    ToolMediaArtifact,
    ToolMediaItem,
)
from neuron_server.tools.document_utils import count_tokens, truncate_response

# Default token limit to prevent context issues
DEFAULT_TOKEN_LIMIT = 20000

# Alpha Vantage API rate limits (free tier)
ALPHAVANTAGE_MINUTE_LIMIT = 5
ALPHAVANTAGE_DAILY_LIMIT = 500


class AlphaVantageRateLimitError(Exception):
    """Raised when Alpha Vantage API rate limits are exceeded."""

    pass


def parse_rate_limit_response(response_text: str) -> None:
    """Check if response contains rate limit message and raise error if so.

    Args:
        response_text: Raw API response text

    Raises:
        AlphaVantageRateLimitError: If response indicates rate limit exceeded
    """
    try:
        data = json.loads(response_text)
        if (
            "Note" in data
            and "Alpha Vantage" in data["Note"]
            and "call frequency" in data["Note"]
        ):
            raise AlphaVantageRateLimitError(
                "Alpha Vantage API rate limit exceeded. "
                "Tier allows 5 calls per minute and 500 calls per day."
            )
    except json.JSONDecodeError:
        # Not JSON response, continue normal processing
        pass


async def check_and_update_rate_limits() -> None:
    """Check current rate limits and increment counters if within limits.

    Raises:
        AlphaVantageRateLimitError: If rate limits would be exceeded
    """
    now = datetime.now(timezone.utc)
    minute_key = f"alphavantage:rate_limit:minute:{now.strftime('%Y%m%d%H%M')}"
    day_key = f"alphavantage:rate_limit:day:{now.strftime('%Y%m%d')}"

    # Check minute limit
    minute_count = await redis_client.get(minute_key)
    minute_count = int(minute_count) if minute_count else 0

    if minute_count >= ALPHAVANTAGE_MINUTE_LIMIT:
        seconds_to_next_minute = 60 - now.second
        raise AlphaVantageRateLimitError(
            f"Alpha Vantage rate limit exceeded: {ALPHAVANTAGE_MINUTE_LIMIT} "
            f"calls per minute. Try again in {seconds_to_next_minute} seconds."
        )

    # Check daily limit
    day_count = await redis_client.get(day_key)
    day_count = int(day_count) if day_count else 0

    if day_count >= ALPHAVANTAGE_DAILY_LIMIT:
        # Calculate hours until midnight UTC
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
            days=1
        )
        hours_until_reset = int((tomorrow - now).total_seconds() / 3600)
        raise AlphaVantageRateLimitError(
            f"Alpha Vantage daily limit exceeded: {ALPHAVANTAGE_DAILY_LIMIT} "
            f"calls per day. Try again in {hours_until_reset} hours."
        )

    # Increment counters
    await redis_client.incr(minute_key)
    await redis_client.expire(minute_key, 60)  # Expire after 1 minute

    await redis_client.incr(day_key)
    await redis_client.expire(day_key, 86400)  # Expire after 24 hours


def validate_and_sanitize_query_params(query_params: str) -> str:
    """Validate and sanitize query parameters for security.

    Args:
        query_params: Raw query parameter string to validate

    Returns:
        Clean, validated query parameter string

    Raises:
        ValueError: If query parameters are invalid or potentially malicious
    """
    # Basic validation
    if not query_params or not isinstance(query_params, str):
        raise ValueError("Query parameters must be a non-empty string")

    # Check for URL schemes/protocols to prevent hijacking
    if re.search(r"^[a-zA-Z]+://", query_params):
        raise ValueError("Query parameters cannot contain URL schemes or protocols")

    # Check for dangerous characters that could enable injection attacks
    dangerous_chars = ["\0", "\n", "\r", "<", ">", '"']
    if any(char in query_params for char in dangerous_chars):
        raise ValueError("Query parameters contain invalid or dangerous characters")

    # Parse with strict validation
    try:
        parsed = urllib.parse.parse_qsl(
            query_params, strict_parsing=True, keep_blank_values=False
        )
    except ValueError as e:
        raise ValueError(f"Invalid query parameter format: {e}") from e

    if not parsed:
        raise ValueError("No valid parameters found after parsing")

    # Validate parameter names - only allow safe characters
    for key, _value in parsed:
        # Specifically block apikey parameter to prevent API key override
        if key.lower() == "apikey":
            raise ValueError(
                "API key should not be included in query parameters. "
                "It will be added automatically."
            )
        if not re.match(r"^[a-zA-Z0-9_]+$", key):
            raise ValueError(
                f"Invalid parameter name '{key}' - only alphanumeric characters "
                "and underscores are allowed"
            )

    # Return clean, properly encoded query string
    return urllib.parse.urlencode(parsed)


@cache_response(ttl=15 * 60)  # Cache for 15 minutes
async def fetch_alphavantage_data(query_params: str) -> str:
    """Fetch data from Alpha Vantage API with caching."""
    if not config.alphavantage_api_key:
        raise ValueError("Alpha Vantage API key not configured")

    # Validate and sanitize query parameters for security
    try:
        clean_query_params = validate_and_sanitize_query_params(query_params)
    except ValueError as e:
        logger.warning(f"Query parameter validation failed: {e}")
        raise ValueError(f"Invalid query parameters: {e}") from e

    # Check and update rate limits before making API call
    try:
        await check_and_update_rate_limits()
    except AlphaVantageRateLimitError as e:
        logger.warning(f"Alpha Vantage rate limit exceeded: {e}")
        raise ValueError(str(e)) from e

    # Construct secure URL with validated parameters
    base_url = "https://www.alphavantage.co/query"
    url = f"{base_url}?{clean_query_params}&apikey={config.alphavantage_api_key}"

    # Log URL without API key for debugging
    log_url = url.replace(config.alphavantage_api_key, "[REDACTED]")
    logger.debug(f"Alpha Vantage API request: {log_url}")

    async with aiohttp.ClientSession() as session:
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                response_text = await response.text()

                # Check for rate limit message in response
                try:
                    parse_rate_limit_response(response_text)
                except AlphaVantageRateLimitError as e:
                    logger.warning(
                        f"Alpha Vantage rate limit detected in response: {e}"
                    )
                    raise ValueError(str(e)) from e

                return response_text
        except aiohttp.ClientError as e:
            logger.error(f"Alpha Vantage API request failed: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error("Alpha Vantage API request timed out")
            raise


class AlphaVantageToolArgs(BaseModel):
    query_params: str = Field(
        description="""
Alpha Vantage API query parameters (excluding apikey - added automatically).

STOCK DATA (requires symbol=TICKER, supports multiple: AAPL,MSFT):
• OVERVIEW - company fundamentals: function=OVERVIEW&symbol=AAPL,MSFT
• BALANCE_SHEET - balance sheet data: function=BALANCE_SHEET&symbol=GOOGL

MARKET INTELLIGENCE:
• NEWS_SENTIMENT - news analysis:
  function=NEWS_SENTIMENT&tickers=AAPL,MSFT,CRYPTO:BTC,CRYPTO:ETH&limit=10
  Optional: tickers, topics, time_from (20220410T0130), time_to, sort (LATEST), limit

CRYPTOCURRENCY (requires symbol & market):
• DIGITAL_CURRENCY_DAILY - crypto prices:
  function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD

TECHNICAL INDICATORS (requires symbol, interval, time_period):
• SMA - simple moving average: function=SMA&symbol=AAPL&interval=daily&time_period=20

ECONOMIC INDICATORS (no symbol needed):
• REAL_GDP: function=REAL_GDP&interval=quarterly
• TREASURY_YIELD: function=TREASURY_YIELD&interval=monthly&maturity=10year
  Optional: interval (daily/weekly/monthly), maturity (3month/2year/5year/10year/30year)
• FEDERAL_FUNDS_RATE: function=FEDERAL_FUNDS_RATE&interval=monthly
• INFLATION: function=INFLATION
• UNEMPLOYMENT: function=UNEMPLOYMENT

Common patterns: function=FUNCTION_NAME&required_params&optional_params
        """.strip()
    )

    skip_truncation: bool = Field(
        default=False,
        description="Skip automatic response truncation at 20k tokens "
        "(use with caution for large responses)",
    )


class AlphaVantageTool(BaseTool):
    name: str = "alphavantage"
    description: str = """
Access Alpha Vantage financial and economic data API for comprehensive market analysis.

Provides access to stock fundamentals, market intelligence, cryptocurrency data,
technical indicators, and economic indicators with multiple symbol support.
    """.strip()

    args_schema: type[AlphaVantageToolArgs] = AlphaVantageToolArgs
    response_format: str = "content_and_artifact"

    def _run(self, *args: Any, **kwargs: Any) -> tuple[str, list[dict]]:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        query_params: str,
        skip_truncation: bool = False,
    ) -> tuple[str, list[dict]]:
        if not config.alphavantage_api_key or len(config.alphavantage_api_key) == 0:
            error_msg = (
                "Error: Alpha Vantage API key not found. Please set "
                "ALPHAVANTAGE_API_KEY environment variable."
            )
            return error_msg, []

        try:
            # Validate and sanitize query parameters for security
            clean_query_params = validate_and_sanitize_query_params(query_params)

            # Create the API URL without API key for artifact display
            api_url_without_key = (
                f"https://www.alphavantage.co/query?{clean_query_params}"
            )

            # Fetch data from API
            response_text = await fetch_alphavantage_data(query_params)

            # Apply token limiting unless skipped
            if not skip_truncation:
                response_text = truncate_response(response_text, DEFAULT_TOKEN_LIMIT)

            logger.debug(
                f"Alpha Vantage response length: {len(response_text)} characters, "
                f"~{count_tokens(response_text)} tokens"
            )

            # Create search result artifact showing the API call made
            artifact = ToolMediaArtifact(
                media_type="search_result",
                items=[
                    ToolMediaItem(
                        id=uuid.uuid4(),
                        url=api_url_without_key,
                        caption="Alpha Vantage",
                        description="",
                        metadata=ToolArtifactMetadata(
                            query=clean_query_params,
                        ),
                    )
                ],
            )

            return response_text, [artifact.model_dump()]

        except ValueError as e:
            logger.error(f"Alpha Vantage configuration error: {e}")
            error_msg = f"Configuration error: {str(e)}"
            return error_msg, []
        except Exception as e:
            logger.error(f"Alpha Vantage API error: {e}", exc_info=True)
            error_msg = f"Error fetching Alpha Vantage data: {str(e)}"
            return error_msg, []
