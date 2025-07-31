"""Unit tests for AlphaVantageTool."""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from neuron_server.tools.alphavantage_tool import (
    ALPHAVANTAGE_DAILY_LIMIT,
    ALPHAVANTAGE_MINUTE_LIMIT,
    DEFAULT_TOKEN_LIMIT,
    AlphaVantageRateLimitError,
    AlphaVantageTool,
    AlphaVantageToolArgs,
    check_and_update_rate_limits,
    parse_rate_limit_response,
    validate_and_sanitize_query_params,
)


class TestAlphaVantageToolArgs:
    """Test suite for AlphaVantageToolArgs parameter validation."""

    def test_valid_parameters(self) -> None:
        """Test valid parameter combinations."""
        # Test minimal valid parameters
        args = AlphaVantageToolArgs(query_params="function=OVERVIEW&symbol=AAPL")
        assert args.query_params == "function=OVERVIEW&symbol=AAPL"
        assert args.skip_truncation is False  # default

    def test_all_parameters(self) -> None:
        """Test all parameters with valid values."""
        args = AlphaVantageToolArgs(
            query_params="function=NEWS_SENTIMENT&tickers=AAPL,MSFT&limit=10",
            skip_truncation=True,
        )
        assert args.query_params == "function=NEWS_SENTIMENT&tickers=AAPL,MSFT&limit=10"
        assert args.skip_truncation is True

    def test_skip_truncation_default(self) -> None:
        """Test skip_truncation defaults to False."""
        args = AlphaVantageToolArgs(query_params="function=OVERVIEW&symbol=AAPL")
        assert args.skip_truncation is False

    def test_empty_query_params(self) -> None:
        """Test empty query_params is allowed by Pydantic but will fail validation."""
        # Pydantic allows this, but our validation function will catch it
        args = AlphaVantageToolArgs(query_params="")
        assert args.query_params == ""


class TestValidateAndSanitizeQueryParams:
    """Test suite for query parameter validation and sanitization."""

    def test_valid_query_params(self) -> None:
        """Test valid query parameter combinations."""
        # Basic stock query
        result = validate_and_sanitize_query_params("function=OVERVIEW&symbol=AAPL")
        assert result == "function=OVERVIEW&symbol=AAPL"

        # Multiple symbols
        result = validate_and_sanitize_query_params(
            "function=NEWS_SENTIMENT&tickers=AAPL,MSFT&limit=10"
        )
        assert "function=NEWS_SENTIMENT" in result
        assert "tickers=AAPL%2CMSFT" in result or "tickers=AAPL,MSFT" in result
        assert "limit=10" in result

    def test_empty_string(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            validate_and_sanitize_query_params("")

    def test_none_input(self) -> None:
        """Test None input raises ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            validate_and_sanitize_query_params(None)

    def test_api_key_parameter_blocked(self) -> None:
        """Test that apikey parameter is blocked."""
        with pytest.raises(ValueError, match="API key should not be included"):
            validate_and_sanitize_query_params("function=OVERVIEW&apikey=test123")

        with pytest.raises(ValueError, match="API key should not be included"):
            validate_and_sanitize_query_params("function=OVERVIEW&APIKEY=test123")

    def test_dangerous_characters(self) -> None:
        """Test dangerous characters are blocked."""
        dangerous_inputs = [
            "function=OVERVIEW<script>alert('xss')</script>",
            "function=OVERVIEW&symbol=AAPL\x00",
            "function=OVERVIEW&symbol=AAPL\n",
            "function=OVERVIEW&symbol=AAPL\r",
            'function=OVERVIEW&symbol="malicious"',
        ]

        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValueError, match="invalid or dangerous characters"):
                validate_and_sanitize_query_params(dangerous_input)

    def test_url_schemes_blocked(self) -> None:
        """Test URL schemes are blocked to prevent hijacking."""
        scheme_inputs = [
            "http://example.com/function=OVERVIEW",
            "https://malicious.com/function=OVERVIEW",
            "ftp://example.com/function=OVERVIEW",
        ]

        for scheme_input in scheme_inputs:
            with pytest.raises(ValueError, match="cannot contain URL schemes"):
                validate_and_sanitize_query_params(scheme_input)

    def test_invalid_parameter_names(self) -> None:
        """Test invalid parameter names are rejected."""
        with pytest.raises(ValueError, match="Invalid parameter name"):
            validate_and_sanitize_query_params("function-invalid=OVERVIEW&symbol=AAPL")

        with pytest.raises(ValueError, match="Invalid parameter name"):
            validate_and_sanitize_query_params("function@invalid=OVERVIEW&symbol=AAPL")


class TestParseRateLimitResponse:
    """Test suite for Alpha Vantage rate limit response parsing."""

    def test_rate_limit_detected(self) -> None:
        """Test rate limit message is detected correctly."""
        rate_limit_response = json.dumps(
            {
                "Note": (
                    "Thank you for using Alpha Vantage! Our standard API call "
                    "frequency is 5 calls per minute and 500 calls per day."
                )
            }
        )

        with pytest.raises(AlphaVantageRateLimitError, match="API rate limit exceeded"):
            parse_rate_limit_response(rate_limit_response)

    def test_normal_response_passes(self) -> None:
        """Test normal API responses pass through without error."""
        normal_response = json.dumps(
            {
                "Meta Data": {
                    "1. Information": (
                        "Daily Prices (open, high, low, close) and Volumes"
                    ),
                    "2. Symbol": "AAPL",
                }
            }
        )

        # Should not raise any exception
        parse_rate_limit_response(normal_response)

    def test_invalid_json_passes(self) -> None:
        """Test invalid JSON responses pass through without error."""
        invalid_json = "This is not valid JSON"

        # Should not raise any exception
        parse_rate_limit_response(invalid_json)

    def test_partial_rate_limit_message(self) -> None:
        """Test partial rate limit messages don't trigger false positives."""
        partial_response = json.dumps({"Note": "Thank you for using Alpha Vantage!"})

        # Should not raise exception (missing "call frequency")
        parse_rate_limit_response(partial_response)


class TestCheckAndUpdateRateLimits:
    """Test suite for Redis-based rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limits_within_bounds(self) -> None:
        """Test rate limiting when within bounds."""
        with patch("neuron_server.tools.alphavantage_tool.redis_client") as mock_redis:
            # Mock Redis to return counts within limits
            mock_redis.get = AsyncMock(
                side_effect=[
                    "3",  # minute count
                    "100",  # day count
                ]
            )
            mock_redis.incr = AsyncMock()
            mock_redis.expire = AsyncMock()

            # Should not raise any exception
            await check_and_update_rate_limits()

            # Verify Redis operations
            assert mock_redis.get.call_count == 2
            assert mock_redis.incr.call_count == 2
            assert mock_redis.expire.call_count == 2

    @pytest.mark.asyncio
    async def test_minute_limit_exceeded(self) -> None:
        """Test minute rate limit exceeded."""
        with patch("neuron_server.tools.alphavantage_tool.redis_client") as mock_redis:
            # Mock Redis to return minute limit exceeded
            mock_redis.get = AsyncMock(
                side_effect=[
                    str(ALPHAVANTAGE_MINUTE_LIMIT),  # at limit
                    "100",  # day count
                ]
            )

            with pytest.raises(AlphaVantageRateLimitError) as exc_info:
                await check_and_update_rate_limits()

            error_msg = str(exc_info.value)
            assert f"{ALPHAVANTAGE_MINUTE_LIMIT} calls per minute" in error_msg
            assert "Try again in" in error_msg
            assert "seconds" in error_msg

    @pytest.mark.asyncio
    async def test_daily_limit_exceeded(self) -> None:
        """Test daily rate limit exceeded."""
        with patch("neuron_server.tools.alphavantage_tool.redis_client") as mock_redis:
            # Mock Redis to return daily limit exceeded
            mock_redis.get = AsyncMock(
                side_effect=[
                    "3",  # minute count
                    str(ALPHAVANTAGE_DAILY_LIMIT),  # at daily limit
                ]
            )

            with pytest.raises(AlphaVantageRateLimitError) as exc_info:
                await check_and_update_rate_limits()

            error_msg = str(exc_info.value)
            assert f"{ALPHAVANTAGE_DAILY_LIMIT} calls per day" in error_msg
            assert "Try again in" in error_msg
            assert "hours" in error_msg

    @pytest.mark.asyncio
    async def test_no_existing_counts(self) -> None:
        """Test rate limiting with no existing Redis counts."""
        with patch("neuron_server.tools.alphavantage_tool.redis_client") as mock_redis:
            # Mock Redis to return None (no existing counts)
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.incr = AsyncMock()
            mock_redis.expire = AsyncMock()

            # Should not raise any exception
            await check_and_update_rate_limits()

            # Verify Redis operations
            assert mock_redis.get.call_count == 2
            assert mock_redis.incr.call_count == 2
            assert mock_redis.expire.call_count == 2


class TestAlphaVantageTool:
    """Test suite for AlphaVantageTool functionality."""

    @pytest.fixture
    def tool(self) -> AlphaVantageTool:
        """Create an AlphaVantageTool instance."""
        return AlphaVantageTool()

    @pytest.fixture
    def sample_api_response(self) -> str:
        """Create sample Alpha Vantage API response."""
        return json.dumps(
            {
                "Meta Data": {
                    "1. Information": (
                        "Daily Prices (open, high, low, close) and Volumes"
                    ),
                    "2. Symbol": "AAPL",
                    "3. Last Refreshed": "2023-12-01",
                    "4. Output Size": "Compact",
                    "5. Time Zone": "US/Eastern",
                },
                "Time Series (Daily)": {
                    "2023-12-01": {
                        "1. open": "189.97",
                        "2. high": "190.67",
                        "3. low": "189.25",
                        "4. close": "191.24",
                        "5. volume": "48744366",
                    }
                },
            }
        )

    def test_tool_properties(self, tool: AlphaVantageTool) -> None:
        """Test tool properties are correctly set."""
        assert tool.name == "alphavantage"
        assert "Alpha Vantage financial and economic data API" in tool.description
        assert tool.args_schema == AlphaVantageToolArgs
        assert tool.response_format == "content_and_artifact"

    @pytest.mark.asyncio
    async def test_missing_api_key(self, tool: AlphaVantageTool) -> None:
        """Test handling of missing API key."""
        with patch("neuron_server.tools.alphavantage_tool.config") as mock_config:
            mock_config.alphavantage_api_key = ""

            result = await tool._arun("function=OVERVIEW&symbol=AAPL")

            assert isinstance(result, tuple)
            assert len(result) == 2
            content, artifacts = result

            assert "API key not found" in content
            assert artifacts == []

    @pytest.mark.asyncio
    async def test_successful_api_call(
        self, tool: AlphaVantageTool, sample_api_response: str
    ) -> None:
        """Test successful API call with artifact generation."""
        query_params = "function=OVERVIEW&symbol=AAPL"

        with (
            patch("neuron_server.tools.alphavantage_tool.config") as mock_config,
            patch(
                "neuron_server.tools.alphavantage_tool.fetch_alphavantage_data"
            ) as mock_fetch,
        ):
            mock_config.alphavantage_api_key = "test_api_key"
            mock_fetch.return_value = sample_api_response

            result = await tool._arun(query_params, skip_truncation=True)

            # Verify tuple return format
            assert isinstance(result, tuple)
            assert len(result) == 2
            content, artifacts = result

            # Verify content
            assert content == sample_api_response
            assert "Meta Data" in content

            # Verify artifacts
            assert isinstance(artifacts, list)
            assert len(artifacts) == 1

            artifact = artifacts[0]
            assert artifact["media_type"] == "search_result"
            assert len(artifact["items"]) == 1

            item = artifact["items"][0]
            assert "https://www.alphavantage.co/query?" in item["url"]
            assert "function=OVERVIEW" in item["url"]
            assert "symbol=AAPL" in item["url"]
            assert "apikey" not in item["url"]  # API key should not be in URL
            assert item["caption"] == "Alpha Vantage"
            assert item["description"] == ""  # Should be empty as requested
            assert item["metadata"]["query"] == query_params

    @pytest.mark.asyncio
    async def test_token_truncation(self, tool: AlphaVantageTool) -> None:
        """Test token truncation functionality."""
        # Create a very long response that exceeds DEFAULT_TOKEN_LIMIT
        long_response = "x" * (DEFAULT_TOKEN_LIMIT * 10)  # Way over limit

        query_params = "function=OVERVIEW&symbol=AAPL"

        with (
            patch("neuron_server.tools.alphavantage_tool.config") as mock_config,
            patch(
                "neuron_server.tools.alphavantage_tool.fetch_alphavantage_data"
            ) as mock_fetch,
        ):
            mock_config.alphavantage_api_key = "test_api_key"
            mock_fetch.return_value = long_response

            # Test with truncation enabled (default)
            result = await tool._arun(query_params, skip_truncation=False)
            content, artifacts = result

            assert len(content) < len(long_response)
            assert "RESPONSE TRUNCATED" in content

            # Test with truncation disabled
            result = await tool._arun(query_params, skip_truncation=True)
            content, artifacts = result

            assert content == long_response
            assert "RESPONSE TRUNCATED" not in content

    @pytest.mark.asyncio
    async def test_invalid_query_params(self, tool: AlphaVantageTool) -> None:
        """Test handling of invalid query parameters."""
        invalid_query = "function=OVERVIEW&apikey=malicious"

        with patch("neuron_server.tools.alphavantage_tool.config") as mock_config:
            mock_config.alphavantage_api_key = "test_api_key"

            result = await tool._arun(invalid_query)

            assert isinstance(result, tuple)
            content, artifacts = result

            assert "Configuration error" in content
            assert "API key should not be included" in content
            assert artifacts == []

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, tool: AlphaVantageTool) -> None:
        """Test handling of rate limit errors."""
        query_params = "function=OVERVIEW&symbol=AAPL"

        with (
            patch("neuron_server.tools.alphavantage_tool.config") as mock_config,
            patch(
                "neuron_server.tools.alphavantage_tool.check_and_update_rate_limits"
            ) as mock_rate_check,
        ):
            mock_config.alphavantage_api_key = "test_api_key"
            mock_rate_check.side_effect = AlphaVantageRateLimitError(
                "Rate limit exceeded: 5 calls per minute. Try again in 30 seconds."
            )

            result = await tool._arun(query_params)

            assert isinstance(result, tuple)
            content, artifacts = result

            assert "Configuration error" in content
            assert "Rate limit exceeded" in content
            assert artifacts == []

    @pytest.mark.asyncio
    async def test_network_error(self, tool: AlphaVantageTool) -> None:
        """Test handling of network errors."""
        query_params = "function=OVERVIEW&symbol=AAPL"

        with (
            patch("neuron_server.tools.alphavantage_tool.config") as mock_config,
            patch(
                "neuron_server.tools.alphavantage_tool.fetch_alphavantage_data"
            ) as mock_fetch,
        ):
            mock_config.alphavantage_api_key = "test_api_key"
            mock_fetch.side_effect = Exception("Network connection failed")

            result = await tool._arun(query_params)

            assert isinstance(result, tuple)
            content, artifacts = result

            assert "Error fetching Alpha Vantage data" in content
            assert "Network connection failed" in content
            assert artifacts == []

    def test_sync_run_method(self, tool: AlphaVantageTool) -> None:
        """Test synchronous _run method delegates to async _arun."""
        with (
            patch.object(tool, "_arun", return_value=("mocked result", [])),
            patch("asyncio.run") as mock_asyncio_run,
        ):
            mock_asyncio_run.return_value = ("mocked result", [])

            result = tool._run(query_params="function=OVERVIEW&symbol=AAPL")

            assert result == ("mocked result", [])
            mock_asyncio_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_artifact_structure(
        self, tool: AlphaVantageTool, sample_api_response: str
    ) -> None:
        """Test detailed artifact structure validation."""
        query_params = "function=NEWS_SENTIMENT&tickers=AAPL,MSFT&limit=10"

        with (
            patch("neuron_server.tools.alphavantage_tool.config") as mock_config,
            patch(
                "neuron_server.tools.alphavantage_tool.fetch_alphavantage_data"
            ) as mock_fetch,
        ):
            mock_config.alphavantage_api_key = "test_api_key"
            mock_fetch.return_value = sample_api_response

            result = await tool._arun(query_params)
            content, artifacts = result

            # Detailed artifact validation
            assert len(artifacts) == 1
            artifact = artifacts[0]

            # Check artifact structure
            required_keys = ["type", "media_type", "items"]
            for key in required_keys:
                assert key in artifact

            assert artifact["type"] == "media"
            assert artifact["media_type"] == "search_result"

            # Check item structure
            item = artifact["items"][0]
            required_item_keys = ["id", "url", "caption", "description", "metadata"]
            for key in required_item_keys:
                assert key in item

            # Validate UUID format
            if isinstance(item["id"], str):
                uuid.UUID(item["id"])  # Will raise if not valid UUID string
            else:
                # Already a UUID object, verify it's valid
                assert isinstance(item["id"], uuid.UUID)

            # Check metadata
            metadata = item["metadata"]
            # Query may be URL-encoded, so check key components are present
            assert "function=NEWS_SENTIMENT" in metadata["query"]
            assert "tickers=" in metadata["query"]
            assert "limit=10" in metadata["query"]
            assert "apikey" not in item["url"]

    @pytest.mark.asyncio
    async def test_logging_calls(
        self, tool: AlphaVantageTool, sample_api_response: str
    ) -> None:
        """Test that appropriate logging calls are made."""
        query_params = "function=OVERVIEW&symbol=AAPL"

        with (
            patch("neuron_server.tools.alphavantage_tool.config") as mock_config,
            patch(
                "neuron_server.tools.alphavantage_tool.fetch_alphavantage_data"
            ) as mock_fetch,
            patch("neuron_server.tools.alphavantage_tool.logger") as mock_logger,
        ):
            mock_config.alphavantage_api_key = "test_api_key"
            mock_fetch.return_value = sample_api_response

            await tool._arun(query_params)

            # Verify debug logging was called
            mock_logger.debug.assert_called()
            log_call_args = mock_logger.debug.call_args[0][0]
            assert "Alpha Vantage response length" in log_call_args
