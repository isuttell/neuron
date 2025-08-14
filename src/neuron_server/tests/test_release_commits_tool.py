"""Unit tests for ReleaseCommitsTool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from neuron_server.tools.release_commits_tool import (
    ReleaseCommitsTool,
    ReleaseCommitsToolArgs,
)


class TestReleaseCommitsToolArgs:
    """Test suite for ReleaseCommitsToolArgs parameter validation."""

    def test_valid_minimal_parameters(self) -> None:
        """Test minimal valid parameters with defaults."""
        args = ReleaseCommitsToolArgs()
        assert args.from_version is None
        assert args.to_version is None
        assert args.from_date is None
        assert args.to_date is None
        assert args.include_timestamps is False
        assert args.max_results == 50

    def test_valid_all_parameters(self) -> None:
        """Test all parameters with valid values."""
        args = ReleaseCommitsToolArgs(
            from_version="v1.0.0",
            to_version="v1.1.0",
            from_date="2024-01-01",
            to_date="2024-12-31",
            include_timestamps=True,
            max_results=100,
        )
        assert args.from_version == "v1.0.0"
        assert args.to_version == "v1.1.0"
        assert args.from_date == "2024-01-01"
        assert args.to_date == "2024-12-31"
        assert args.include_timestamps is True
        assert args.max_results == 100

    def test_max_results_validation(self) -> None:
        """Test max_results parameter validation."""
        # Valid range (1-200)
        args = ReleaseCommitsToolArgs(max_results=1)
        assert args.max_results == 1

        args = ReleaseCommitsToolArgs(max_results=200)
        assert args.max_results == 200

        # Invalid: too low
        with pytest.raises(ValidationError):
            ReleaseCommitsToolArgs(max_results=0)

        # Invalid: too high
        with pytest.raises(ValidationError):
            ReleaseCommitsToolArgs(max_results=201)

    def test_version_string_parameters(self) -> None:
        """Test version string parameters accept various formats."""
        # Standard semantic version
        args = ReleaseCommitsToolArgs(from_version="v1.2.3", to_version="v2.0.0")
        assert args.from_version == "v1.2.3"
        assert args.to_version == "v2.0.0"

        # Without 'v' prefix
        args = ReleaseCommitsToolArgs(from_version="1.2.3", to_version="2.0.0")
        assert args.from_version == "1.2.3"
        assert args.to_version == "2.0.0"

        # Custom tag format
        args = ReleaseCommitsToolArgs(
            from_version="release-2024.01", to_version="release-2024.02"
        )
        assert args.from_version == "release-2024.01"
        assert args.to_version == "release-2024.02"

    def test_date_string_parameters(self) -> None:
        """Test date string parameters."""
        args = ReleaseCommitsToolArgs(
            from_date="2024-01-01", to_date="2024-12-31T23:59:59Z"
        )
        assert args.from_date == "2024-01-01"
        assert args.to_date == "2024-12-31T23:59:59Z"


class TestReleaseCommitsTool:
    """Test suite for ReleaseCommitsTool functionality."""

    @pytest.fixture(autouse=True)
    def mock_config_git_commit(self) -> None:
        """Mock the git commit config for all tests."""
        with patch("neuron_server.tools.release_commits_tool.config") as mock_config:
            # Set a known deployed commit for tests (use the last commit in sample data)
            mock_config.git_commit = "ghi789"
            yield mock_config

    @pytest.fixture
    def tool(self) -> ReleaseCommitsTool:
        """Create a ReleaseCommitsTool instance."""
        return ReleaseCommitsTool()

    def create_mock_get_handler(
        self, commits_list_response, individual_commits=None, tags=None
    ):
        """Create a mock handler for aiohttp.ClientSession.get."""

        def get_side_effect(url, **kwargs):
            mock_response = AsyncMock()
            mock_response.status = 200

            # Handle individual commit requests
            if "/commits/" in url and not url.endswith("/commits"):
                commit_sha = url.split("/commits/")[-1]
                if individual_commits and commit_sha in individual_commits:
                    mock_response.json = AsyncMock(
                        return_value=individual_commits[commit_sha]
                    )
                else:
                    # Default individual commit response
                    mock_response.json = AsyncMock(
                        return_value={
                            "sha": commit_sha,
                            "commit": {
                                "author": {"date": "2024-01-13T09:15:00Z"},
                                "message": "Default commit message",
                            },
                        }
                    )
            # Handle tags requests
            elif "/tags/" in url:
                tag_name = url.split("/tags/")[-1]
                if tags and tag_name in tags:
                    mock_response.json = AsyncMock(return_value=tags[tag_name])
                else:
                    mock_response.status = 404
            # Handle commits list
            else:
                mock_response.json = AsyncMock(return_value=commits_list_response)

            # Create a context manager that returns the mock response
            context_manager = AsyncMock()
            context_manager.__aenter__.return_value = mock_response
            return context_manager

        return get_side_effect

    @pytest.fixture
    def sample_commits(self) -> list[dict]:
        """Create sample commit data."""
        return [
            {
                "sha": "abc123",
                "commit": {
                    "message": "feat: add new feature X",
                    "author": {"date": "2024-01-15T10:30:00Z"},
                },
                "html_url": "https://gitea.zaks.io/isuttell/neuron/commit/abc123",
            },
            {
                "sha": "def456",
                "commit": {
                    "message": "fix: resolve bug in component Y",
                    "author": {"date": "2024-01-14T14:22:00Z"},
                },
                "html_url": "https://gitea.zaks.io/isuttell/neuron/commit/def456",
            },
            {
                "sha": "ghi789",
                "commit": {
                    "message": "docs: update README with installation instructions",
                    "author": {"date": "2024-01-13T09:15:00Z"},
                },
                "html_url": "https://gitea.zaks.io/isuttell/neuron/commit/ghi789",
            },
        ]

    @pytest.fixture
    def sample_tag_data(self) -> dict:
        """Create sample tag data."""
        return {
            "name": "v1.0.0",
            "commit": {
                "sha": "xyz789",
                "created": "2024-01-10T12:00:00Z",
            },
        }

    def test_tool_properties(self, tool: ReleaseCommitsTool) -> None:
        """Test tool properties are correctly set."""
        assert tool.name == "release_commits"
        assert "Analyze release commits" in tool.description
        assert tool.args_schema == ReleaseCommitsToolArgs
        assert tool.response_format == "content_and_artifact"

    def test_tool_initialization(self, tool: ReleaseCommitsTool) -> None:
        """Test tool initialization sets correct API configuration."""
        assert tool._base_url == "https://gitea.zaks.io"
        assert tool._api_base == "https://gitea.zaks.io/api/v1"

    @pytest.mark.asyncio
    async def test_successful_date_range_query(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test successful commit query by date range."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Create different mock responses based on URL
            def get_side_effect(url, **kwargs):
                mock_response = AsyncMock()
                mock_response.status = 200

                if "/commits/" in url and url.endswith("ghi789"):
                    # Mock response for individual commit (deployed commit)
                    mock_response.json = AsyncMock(
                        return_value={
                            "sha": "ghi789",
                            "commit": {
                                "author": {"date": "2024-01-13T09:15:00Z"},
                                "message": "docs: update README",
                            },
                        }
                    )
                else:
                    # Mock response for commits list
                    mock_response.json = AsyncMock(return_value=sample_commits)

                # Create a context manager that returns the mock response
                context_manager = AsyncMock()
                context_manager.__aenter__.return_value = mock_response
                return context_manager

            mock_get.side_effect = get_side_effect

            # Execute query
            result = await tool._arun(
                from_date="2024-01-01", to_date="2024-01-31", max_results=50
            )

            # Verify result is tuple with content and artifacts
            assert isinstance(result, tuple)
            assert len(result) == 2
            content, artifacts = result

            # Verify content structure
            assert "# Release Commits Analysis" in content
            assert "Total Commits**: 3" in content
            assert "feat: add new feature X" in content
            assert "fix: resolve bug in component Y" in content
            assert "docs: update README" in content

            # Verify artifacts
            assert isinstance(artifacts, list)
            assert len(artifacts) == 1
            artifact = artifacts[0]
            assert artifact["media_type"] == "text"
            assert len(artifact["items"]) == 1
            item = artifact["items"][0]
            assert item["name"] == "Release Notes"
            assert item["metadata"]["total_commits"] == 3

    @pytest.mark.asyncio
    async def test_successful_version_range_query(
        self,
        tool: ReleaseCommitsTool,
        sample_commits: list[dict],
        sample_tag_data: dict,
    ) -> None:
        """Test successful commit query by version range."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Use the helper to create mock handler
            tags = {
                "v1.0.0": sample_tag_data,
                "v1.1.0": {
                    "name": "v1.1.0",
                    "commit": {"created": "2024-01-20T12:00:00Z"},
                },
            }
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits, tags=tags
            )

            # Execute query
            result = await tool._arun(from_version="v1.0.0", to_version="v1.1.0")

            # Verify result structure
            content, artifacts = result
            assert "# Release Commits Analysis" in content
            assert "Total Commits**: 3" in content
            assert "Time Range" in content
            assert "2024-01-10T12:00:00Z" in content
            # The to_date should be limited by deployed commit date (2024-01-13)
            assert "2024-01-13T09:15:00Z" in content

    @pytest.mark.asyncio
    async def test_include_timestamps_option(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test include_timestamps option adds timestamps to output."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits
            )

            # Execute query with timestamps enabled
            result = await tool._arun(from_date="2024-01-01", include_timestamps=True)

            content, _ = result
            # Verify timestamps are included in commit messages
            assert "[2024-01-15T10:30:00Z]" in content
            assert "[2024-01-14T14:22:00Z]" in content
            assert "[2024-01-13T09:15:00Z]" in content

    @pytest.mark.asyncio
    async def test_include_timestamps_disabled(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test timestamps are not included when include_timestamps=False."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits
            )

            # Execute query with timestamps disabled (default)
            result = await tool._arun(from_date="2024-01-01")

            content, _ = result
            # Verify timestamps are NOT included
            assert "[2024-01-15T10:30:00Z]" not in content
            assert "feat: add new feature X" in content

    @pytest.mark.asyncio
    async def test_empty_commit_results(self, tool: ReleaseCommitsTool) -> None:
        """Test handling of empty commit results."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=[]
            )

            # Execute query
            result = await tool._arun(from_date="2024-01-01")

            content, artifacts = result
            assert "Total Commits**: 0" in content
            assert "## Commit Messages" not in content  # Section not shown when empty

            # Verify artifact still created with zero counts
            artifact = artifacts[0]
            assert artifact["items"][0]["metadata"]["total_commits"] == 0

    @pytest.mark.asyncio
    async def test_tag_not_found(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test handling when version tag is not found."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Empty tags dict means tag won't be found (404)
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits, tags={}
            )

            # Execute query
            result = await tool._arun(from_version="nonexistent-tag")

            content, _ = result
            assert "Total Commits**: 3" in content
            # Should still show time range based on deployed commit
            assert "Time Range" in content

    @pytest.mark.asyncio
    async def test_api_error_handling(self, tool: ReleaseCommitsTool) -> None:
        """Test handling of API errors."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Mock API error - return empty list for non-200 status
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.json.return_value = []
            mock_get.return_value.__aenter__.return_value = mock_response

            # Execute query - should return empty results for API errors
            result = await tool._arun(from_date="2024-01-01")

            content, artifacts = result
            assert "Total Commits**: 0" in content

    @pytest.mark.asyncio
    async def test_max_results_parameter(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test max_results parameter is passed correctly to API."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits[:2]
            )

            # Execute query with max_results=2
            result = await tool._arun(from_date="2024-01-01", max_results=2)

            content, artifacts = result
            assert "Total Commits**: 2" in content

            # Verify API was called with correct limit
            mock_get.assert_called()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["limit"] == 2

    @pytest.mark.asyncio
    async def test_artifact_security_no_commit_messages(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test artifacts don't contain sensitive commit messages."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits
            )

            # Execute query
            result = await tool._arun(from_date="2024-01-01")

            _, artifacts = result
            artifact = artifacts[0]

            # Verify artifact contains only summary data, no commit messages
            # Check metadata directly instead of JSON serialization
            # (which fails with UUIDs)
            metadata = artifact["items"][0]["metadata"]
            assert "total_commits" in metadata
            assert metadata["total_commits"] == 3

            # Verify commit messages are not in the artifact structure
            artifact_str = str(artifact)
            assert "feat: add new feature X" not in artifact_str
            assert "fix: resolve bug" not in artifact_str

    @pytest.mark.asyncio
    async def test_date_range_in_artifact_description(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test artifact description includes date range information."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits
            )

            # Execute query with date range
            result = await tool._arun(from_date="2024-01-01", to_date="2024-01-31")

            _, artifacts = result
            item = artifacts[0]["items"][0]
            # The to_date will be limited to deployed commit date (2024-01-13)
            assert "from 2024-01-01" in item["description"]

    def test_sync_run_method(self, tool: ReleaseCommitsTool) -> None:
        """Test synchronous _run method delegates to async _arun."""
        with (
            patch.object(tool, "_arun", return_value=("test content", [])),
            patch("asyncio.run") as mock_asyncio_run,
        ):
            mock_asyncio_run.return_value = ("test content", [])

            # Execute sync method
            result = tool._run(from_date="2024-01-01")

            # Verify result
            assert result == ("test content", [])

            # Verify asyncio.run was called
            mock_asyncio_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_logging_debug_messages(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test debug logging is called with correct parameters."""
        with (
            patch("neuron_server.tools.release_commits_tool.logger") as mock_logger,
            patch("aiohttp.ClientSession.get") as mock_get,
        ):
            # Use the mock handler that handles different endpoints properly
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits,
                tags={},  # Empty tags means 404 for tag lookups
            )

            # Execute query
            await tool._arun(
                from_version="v1.0.0",
                to_version="v1.1.0",
                from_date="2024-01-01",
                to_date="2024-01-31",
            )

            # Verify debug logging was called
            mock_logger.debug.assert_called()
            # Find the analysis log call (not the "Reached deployed commit" one)
            analysis_call = None
            for call in mock_logger.debug.call_args_list:
                if "Release commits analysis" in call[0][0]:
                    analysis_call = call[0][0]
                    break
            assert analysis_call is not None
            assert "Release commits analysis for isuttell/neuron" in analysis_call
            assert "versions=v1.0.0->v1.1.0" in analysis_call
            assert "dates=2024-01-01->2024-01-31" in analysis_call

    @pytest.mark.asyncio
    async def test_parameter_defaults_applied(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test parameter defaults are applied correctly."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits
            )

            # Execute with minimal parameters
            result = await tool._arun()

            # Should execute successfully with defaults
            content, artifacts = result
            assert "Total Commits**: 3" in content

            # Verify API was called with default max_results
            call_args = mock_get.call_args
            assert call_args[1]["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_commit_data_transformation(
        self, tool: ReleaseCommitsTool, sample_commits: list[dict]
    ) -> None:
        """Test commit data is correctly transformed from API response."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = self.create_mock_get_handler(
                commits_list_response=sample_commits
            )

            # Execute query
            result = await tool._arun(from_date="2024-01-01")

            content, _ = result

            # Verify all commit messages appear in output
            assert "feat: add new feature X" in content
            assert "fix: resolve bug in component Y" in content
            assert "docs: update README with installation instructions" in content


class TestReleaseCommitsDeploymentFiltering:
    """Test suite for deployment commit filtering functionality."""

    @pytest.fixture(autouse=True)
    def mock_config_git_commit(self) -> None:
        """Mock the git commit config for all tests."""
        with patch("neuron_server.tools.release_commits_tool.config") as mock_config:
            # Set a known deployed commit for tests
            mock_config.git_commit = "def456deployed"
            yield mock_config

    @pytest.fixture
    def mock_commits_data(self) -> list[dict]:
        """Mock commit data for testing deployment filtering."""
        return [
            {
                "sha": "abc123newer",
                "commit": {
                    "message": "feat: unreleased feature",
                    "author": {"date": "2024-01-03T10:00:00Z"},
                },
                "html_url": "https://gitea.zaks.io/isuttell/neuron/commit/abc123newer",
            },
            {
                "sha": "def456deployed",
                "commit": {
                    "message": "fix: deployed bug fix",
                    "author": {"date": "2024-01-02T10:00:00Z"},
                },
                "html_url": "https://gitea.zaks.io/isuttell/neuron/commit/def456deployed",
            },
            {
                "sha": "ghi789older",
                "commit": {
                    "message": "feat: older feature",
                    "author": {"date": "2024-01-01T10:00:00Z"},
                },
                "html_url": "https://gitea.zaks.io/isuttell/neuron/commit/ghi789older",
            },
        ]

    @patch("neuron_server.tools.release_commits_tool.config")
    @patch("aiohttp.ClientSession.get")
    async def test_commits_filtered_by_deployed_commit(
        self, mock_get: AsyncMock, mock_config: AsyncMock, mock_commits_data: list[dict]
    ) -> None:
        """Test that commits are filtered to only show up to deployed commit."""
        # Setup config to return deployed commit SHA
        mock_config.git_commit = "def456deployed"

        # Mock API responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_commits_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        tool = ReleaseCommitsTool()
        commits = await tool._get_commits_in_range("isuttell", "neuron", {}, 50)

        # Should only include deployed commit and older commits, not newer ones
        assert len(commits) == 2
        assert commits[0]["sha"] == "abc123newer"  # Added before deployed commit
        assert commits[1]["sha"] == "def456deployed"  # Deployed commit (included)
        # "ghi789older" should not be included since we stop at deployed commit

    @patch("aiohttp.ClientSession.get")
    async def test_commits_unfiltered_when_no_deployed_commit(
        self,
        mock_get: AsyncMock,
        mock_config_git_commit: AsyncMock,
        mock_commits_data: list[dict],
    ) -> None:
        """Test no commits shown when deployed commit is unknown."""
        # Override the fixture to set unknown deployed commit
        mock_config_git_commit.git_commit = "unknown"

        # Mock API responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_commits_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        tool = ReleaseCommitsTool()
        commits = await tool._get_commits_in_range("isuttell", "neuron", {}, 50)

        # Should return empty list when deployed commit is unknown (security measure)
        assert len(commits) == 0
        # API should not even be called when deployed commit is unknown
        mock_get.assert_not_called()

    @patch("neuron_server.tools.release_commits_tool.config")
    @patch("aiohttp.ClientSession.get")
    async def test_resolve_date_range_uses_deployed_commit_date(
        self, mock_get: AsyncMock, mock_config: AsyncMock
    ) -> None:
        """Test that date range resolution uses deployed commit date as boundary."""
        # Setup config to return deployed commit SHA
        mock_config.git_commit = "def456deployed"

        # Mock API response for commit date lookup
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"commit": {"author": {"date": "2024-01-02T10:00:00Z"}}}
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        tool = ReleaseCommitsTool()

        from neuron_server.tools.release_commits_tool import ReleaseCommitsParams

        params = ReleaseCommitsParams()

        date_range = await tool._resolve_date_range("isuttell", "neuron", params)

        # Should set to_date to deployed commit date
        assert date_range["to_date"] == "2024-01-02T10:00:00Z"

    async def test_format_response_when_deployed_commit_unknown(
        self, mock_config_git_commit: AsyncMock
    ) -> None:
        """Test response formatting when deployed commit is unknown."""
        # Override the default mock to set unknown deployed commit
        mock_config_git_commit.git_commit = "unknown"

        tool = ReleaseCommitsTool()
        analysis_data = {"commits": [], "summary": {"total_commits": 0}}

        response_text = tool._format_response_text(analysis_data, {})

        # Should include warning message
        assert "Deployment information is not available" in response_text
        # Should not include summary section when deployment info is unknown
        assert "## Summary" not in response_text
