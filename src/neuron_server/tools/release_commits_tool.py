import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp
from langchain.tools import BaseTool
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from pydantic import BaseModel, Field

from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.tools.artifact_types import (
    ToolArtifactMetadata,
    ToolMediaArtifact,
    ToolMediaItem,
)

# Constants
HTTP_OK = 200


@dataclass
class ReleaseCommitsParams:
    """Parameters for release commits analysis."""

    from_version: str | None = None
    to_version: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    include_timestamps: bool = False
    max_results: int = 50


class ReleaseCommitsToolArgs(BaseModel):
    from_version: str | None = Field(
        description="Start version tag (e.g., 'v1.2.0')", default=None
    )
    to_version: str | None = Field(
        description="End version tag (e.g., 'v1.3.0')", default=None
    )
    from_date: str | None = Field(
        description="Start date in ISO format (YYYY-MM-DD)", default=None
    )
    to_date: str | None = Field(
        description="End date in ISO format (YYYY-MM-DD)", default=None
    )
    include_timestamps: bool = Field(
        description="Whether to include commit timestamps in the response",
        default=False,
    )
    max_results: int = Field(
        description="Maximum number of commits to return",
        default=50,
        ge=1,
        le=200,
    )


class ReleaseCommitsTool(BaseTool):
    name: str = "release_commits"
    description: str = """
Analyze release commits to generate release notes and understand code changes over time.
Can search by version tags or date ranges to provide clean commit-based analysis.

Features:
- Query commits between version tags or date ranges
- Generate release notes from commit messages
- Support for both version-based and time-based analysis
- Clean commit history without technical details
- Automatically limits results to deployed version (only shows live features)

Use this tool to generate release notes and understand code changes over time.
Only shows commits that are actually deployed - no unreleased features displayed.
Note: Do not include developer related information in responses. This tool is for users
who only interact through the UI. Use this tool to help users understand new features,
and bug fixes, but do not include things like logging changes for example.
""".strip()
    args_schema: type[ReleaseCommitsToolArgs] = ReleaseCommitsToolArgs
    response_format: str = "content_and_artifact"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Store API configuration as class constants
        self._base_url = "https://gitea.zaks.io"
        self._api_base = f"{self._base_url}/api/v1"

    def _run(  # noqa: PLR0913
        self,
        from_version: str | None = None,
        to_version: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        include_timestamps: bool = False,
        max_results: int = 50,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> tuple[str, list[dict]]:
        """Synchronous implementation that delegates to async version."""
        params = ReleaseCommitsParams(
            from_version=from_version,
            to_version=to_version,
            from_date=from_date,
            to_date=to_date,
            include_timestamps=include_timestamps,
            max_results=max_results,
        )
        return asyncio.run(
            self._arun_internal(
                params=params,
                run_manager=run_manager.get_async() if run_manager else None,
            )
        )

    async def _arun(  # noqa: PLR0913
        self,
        from_version: str | None = None,
        to_version: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        include_timestamps: bool = False,
        max_results: int = 50,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> tuple[str, list[dict]]:
        """Main async implementation."""
        params = ReleaseCommitsParams(
            from_version=from_version,
            to_version=to_version,
            from_date=from_date,
            to_date=to_date,
            include_timestamps=include_timestamps,
            max_results=max_results,
        )
        return await self._arun_internal(params=params, run_manager=run_manager)

    async def _arun_internal(
        self,
        params: ReleaseCommitsParams,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> tuple[str, list[dict]]:
        """Internal async implementation."""
        # Use hardcoded repository configuration
        owner = "isuttell"
        repo = "neuron"

        try:
            logger.debug(
                f"Release commits analysis for {owner}/{repo}: "
                f"versions={params.from_version}->{params.to_version}, "
                f"dates={params.from_date}->{params.to_date}"
            )

            # Prepare analysis data
            analysis_data = {
                "repository": f"{owner}/{repo}",
                "commits": [],
                "summary": {},
            }

            # Determine date range from version tags if needed
            date_range = await self._resolve_date_range(owner, repo, params)

            # Get commits in range
            commits = await self._get_commits_in_range(
                owner, repo, date_range, params.max_results
            )
            analysis_data["commits"] = commits

            # Generate summary statistics
            analysis_data["summary"] = self._generate_summary(analysis_data)

            # Create response text
            response_text = self._format_response_text(
                analysis_data, date_range, params.include_timestamps
            )

            # Create artifacts
            artifacts = self._create_artifacts(analysis_data, date_range)

            return response_text, [artifact.model_dump() for artifact in artifacts]

        except Exception as e:
            logger.error(f"Release commits analysis error: {e}", exc_info=True)
            raise e

    async def _resolve_date_range(
        self, owner: str, repo: str, params: ReleaseCommitsParams
    ) -> dict[str, str | None]:
        """Resolve the date range for analysis."""
        resolved_range = {
            "from_date": params.from_date,
            "to_date": params.to_date,
        }

        # If version tags are provided, get their dates
        if params.from_version or params.to_version:
            if params.from_version:
                tag_date = await self._get_tag_date(owner, repo, params.from_version)
                if tag_date:
                    resolved_range["from_date"] = tag_date

            if params.to_version:
                tag_date = await self._get_tag_date(owner, repo, params.to_version)
                if tag_date:
                    resolved_range["to_date"] = tag_date

        # Always limit to deployed commit date to prevent showing unreleased features
        deployed_commit_date = await self._get_commit_date(
            owner, repo, config.git_commit
        )
        if deployed_commit_date and (
            not resolved_range["to_date"]
            or deployed_commit_date < resolved_range["to_date"]
        ):
            resolved_range["to_date"] = deployed_commit_date

        return resolved_range

    async def _get_tag_date(self, owner: str, repo: str, tag_name: str) -> str | None:
        """Get the date of a specific version tag."""
        async with aiohttp.ClientSession() as session:
            url = f"{self._api_base}/repos/{owner}/{repo}/tags/{tag_name}"
            async with session.get(url) as response:
                if response.status == HTTP_OK:
                    tag_data = await response.json()
                    return tag_data.get("commit", {}).get("created")
                return None

    async def _get_commit_date(
        self, owner: str, repo: str, commit_sha: str
    ) -> str | None:
        """Get the date of a specific commit."""
        if not commit_sha or commit_sha == "unknown":
            return None

        async with aiohttp.ClientSession() as session:
            url = f"{self._api_base}/repos/{owner}/{repo}/commits/{commit_sha}"
            async with session.get(url) as response:
                if response.status == HTTP_OK:
                    commit_data = await response.json()
                    return commit_data.get("commit", {}).get("author", {}).get("date")
                return None

    async def _get_commits_in_range(
        self, owner: str, repo: str, date_range: dict[str, str | None], max_results: int
    ) -> list[dict]:
        """Fetch commits within range, filtered by deployed commit boundary."""
        commits = []
        deployed_commit_sha = config.git_commit

        async with aiohttp.ClientSession() as session:
            url = f"{self._api_base}/repos/{owner}/{repo}/commits"
            query_params = {"limit": max_results}

            if date_range.get("from_date"):
                query_params["since"] = date_range["from_date"]
            if date_range.get("to_date"):
                query_params["until"] = date_range["to_date"]

            async with session.get(url, params=query_params) as response:
                if response.status == HTTP_OK:
                    commit_data = await response.json()
                    for commit in commit_data:
                        commit_sha = commit["sha"]

                        # Stop processing commits if we've reached the deployed commit
                        # This ensures we don't show commits after deployed version
                        if (
                            deployed_commit_sha
                            and deployed_commit_sha != "unknown"
                            and commit_sha == deployed_commit_sha
                        ):
                            # Include the deployed commit itself, then stop
                            commits.append(
                                {
                                    "sha": commit_sha,
                                    "message": commit["commit"]["message"],
                                    "date": commit["commit"]["author"]["date"],
                                    "url": commit["html_url"],
                                }
                            )
                            break

                        commits.append(
                            {
                                "sha": commit_sha,
                                "message": commit["commit"]["message"],
                                "date": commit["commit"]["author"]["date"],
                                "url": commit["html_url"],
                            }
                        )

        return commits

    def _generate_summary(self, analysis_data: dict) -> dict:
        """Generate summary statistics from the analysis data."""
        commits = analysis_data["commits"]

        return {
            "total_commits": len(commits),
        }

    def _format_response_text(
        self, analysis_data: dict, date_range: dict, include_timestamps: bool = False
    ) -> str:
        """Format the response text for the LLM."""
        summary = analysis_data["summary"]
        commits = analysis_data["commits"]

        response_lines = [
            "# Release Commits Analysis",
            "",
            "## Summary",
            f"- **Total Commits**: {summary['total_commits']}",
        ]

        if date_range.get("from_date") or date_range.get("to_date"):
            response_lines.extend(
                [
                    "",
                    "## Time Range",
                    f"- **From**: {date_range.get('from_date', 'Beginning')}",
                    f"- **To**: {date_range.get('to_date', 'Present')}",
                ]
            )

        if commits:
            response_lines.extend(
                [
                    "",
                    "## Commit Messages",
                ]
            )
            for commit in commits:
                commit_line = f"- {commit['message']}"
                if include_timestamps:
                    commit_line += f" [{commit['date']}]"
                response_lines.append(commit_line)

        return "\n".join(response_lines)

    def _create_artifacts(
        self, analysis_data: dict, date_range: dict
    ) -> list[ToolMediaArtifact]:
        """Create media artifacts with summary data only (no sensitive messages)."""
        artifacts = []
        summary = analysis_data["summary"]

        # Build description with date range info if available
        description = "Release commits summary"
        if date_range.get("from_date") or date_range.get("to_date"):
            from_date = date_range.get("from_date", "beginning")
            to_date = date_range.get("to_date", "present")
            description += f" from {from_date} to {to_date}"

        # Create data artifact with only summary information (no raw commit messages)
        artifacts.append(
            ToolMediaArtifact(
                media_type="data",
                items=[
                    ToolMediaItem(
                        id=str(uuid.uuid4()),
                        url="",
                        name="Release Commits Summary",
                        description=description,
                        metadata=ToolArtifactMetadata(
                            type="release_commits",
                            query="Release commits summary",
                            **summary,  # Include summary stats in metadata
                        ),
                    )
                ],
            )
        )

        return artifacts
