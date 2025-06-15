"""Pyodide-based code interpreter tool using LangChain Sandbox."""

import asyncio
import json
import os
import time
from contextlib import suppress
from typing import Any
from uuid import uuid4

import aiofiles
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from langchain_sandbox import PyodideSandbox
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.tools.artifact_types import (
    ToolArtifactMetadata,
    ToolMediaArtifact,
    ToolMediaItem,
)


class PyodideCodeInterpreterToolArgs(BaseModel):
    python_code: str = Field(
        description="""
Python code to execute in a Pyodide WebAssembly sandbox. Code should be
self-contained and focus on computations, data analysis, or simple visualizations.
This environment has fast startup but limited capabilities compared to Docker:

- No file system access (cannot save/load files)
- Limited to packages available in Pyodide
- Network requests require httpx.AsyncClient
- Results must be printed to stdout or returned as variables
- Good for: calculations, data analysis, simple plots as strings
- Not good for: complex file operations, custom library installations

Available packages include: numpy, pandas, matplotlib, scipy, sympy, scikit-learn,
and many others. Use print() statements to show results and progress.
""".strip()
    )
    stateful: bool = Field(
        default=True, description="Whether to maintain state between executions"
    )


class PyodideCodeInterpreterTool(BaseTool):
    name: str = "pyodide_code_interpreter"
    description: str = """
Fast Python code execution using Pyodide WebAssembly sandbox. Ideal for quick
mathematical calculations, data analysis, and computational tasks. Faster startup
than Docker but cannot generate file artifacts. Use for:
- Mathematical computations and analysis
- Data processing with pandas/numpy
- Simple visualizations (as text/string output)
- Statistical calculations
- Algorithm implementations

Limitations: No file I/O, limited package ecosystem compared to full Python.
For complex workflows requiring file generation, use the regular code_interpreter tool.
""".strip()

    args_schema: type[PyodideCodeInterpreterToolArgs] = PyodideCodeInterpreterToolArgs
    response_format: str = "content_and_artifact"

    timeout: int = 120
    _sandbox_cache: dict[str, tuple[PyodideSandbox, bytes, dict]] = {}
    _cleanup_tasks: dict[str, asyncio.Task] = {}

    async def _schedule_cleanup(self, cache_key: str, delay: int = 900) -> None:
        """Schedule cleanup of a cache entry after delay seconds (default 15 min)."""
        await asyncio.sleep(delay)
        if cache_key in self._sandbox_cache:
            del self._sandbox_cache[cache_key]
        if cache_key in self._cleanup_tasks:
            del self._cleanup_tasks[cache_key]

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _create_media_item(
        self,
        url: str,
        media_type: str,
        name: str,
        description: str,
        config: RunnableConfig,
    ) -> MediaItemModel:
        """Helper to create media item with config handling."""
        user_id = config["configurable"].get("user_id")
        if not user_id:
            raise ValueError("User ID is required")

        params = MediaItemModel.CreateParams(
            url=url,
            media_type=media_type,
            user_id=user_id,
            thread_id=config["configurable"].get("thread_id"),
            name=name,
            description=description,
        )
        return await MediaItemModel.create(params)

    async def _write_artifact_files(
        self,
        python_code: str,
        stdout: str,
        stderr: str,
        execution_data: dict,
        artifacts_folder: str,
    ) -> tuple[str, str, str]:
        """Write artifact files and return their URLs."""
        folder_name = os.path.basename(artifacts_folder)
        base_url = f"{neuron_config.static_content_url}/artifacts/{folder_name}"

        # Save the Python code
        code_filename = "source_code.py"
        code_path = os.path.join(artifacts_folder, code_filename)
        async with aiofiles.open(code_path, "w", encoding="utf-8") as f:
            await f.write(python_code)
        code_url = f"{base_url}/{code_filename}"

        # Save the output if any
        output_url = None
        if stdout or stderr:
            output_filename = "output.txt"
            output_path = os.path.join(artifacts_folder, output_filename)
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                if stdout:
                    await f.write("=== STDOUT ===\n")
                    await f.write(stdout)
                    if stderr:
                        await f.write("\n\n")
                if stderr:
                    await f.write("=== STDERR ===\n")
                    await f.write(stderr)
            output_url = f"{base_url}/{output_filename}"

        # Save execution metadata
        metadata_filename = "execution_metadata.json"
        metadata_path = os.path.join(artifacts_folder, metadata_filename)
        async with aiofiles.open(metadata_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(execution_data, indent=2))
        metadata_url = f"{base_url}/{metadata_filename}"

        return code_url, output_url, metadata_url

    async def _create_artifacts(
        self,
        execution_info: dict,  # Contains python_code, stdout, stderr, duration
        urls: tuple[str, str | None, str],  # code_url, output_url, metadata_url
        execution_data: dict,
        config: RunnableConfig | None = None,
    ) -> list:
        """Create artifact items for the execution."""
        artifact_items = []
        code_url, output_url, metadata_url = urls
        python_code = execution_info["python_code"]
        stdout = execution_info["stdout"]
        stderr = execution_info["stderr"]
        duration = execution_info["duration"]

        # Create media item for code
        code_media_item = await self._create_media_item(
            url=code_url,
            media_type="code",
            name="source_code.py",
            description=f"Python code ({len(python_code.splitlines())} lines)",
            config=config,
        )

        artifact_items.append(
            ToolMediaItem(
                id=str(code_media_item.id),
                url=code_url,
                caption="Source Code",
                description=f"Python code ({len(python_code.splitlines())} lines)",
                metadata=ToolArtifactMetadata(
                    output_format="python",
                    code_lines=len(python_code.splitlines()),
                ),
            )
        )

        # Create media item for output if exists
        if output_url:
            output_media_item = await self._create_media_item(
                url=output_url,
                media_type="data",
                name="output.txt",
                description="Execution output",
                config=config,
            )

            artifact_items.append(
                ToolMediaItem(
                    id=str(output_media_item.id),
                    url=output_url,
                    caption="Execution Output",
                    description="stdout and stderr from execution",
                    metadata=ToolArtifactMetadata(
                        output_format="text",
                        has_output=bool(stdout),
                        has_errors=bool(stderr),
                    ),
                )
            )

        # Create media item for metadata
        metadata_media_item = await self._create_media_item(
            url=metadata_url,
            media_type="data",
            name="execution_metadata.json",
            description="Execution metadata and variables",
            config=config,
        )

        variables = execution_data.get("variables", {})
        artifact_items.append(
            ToolMediaItem(
                id=str(metadata_media_item.id),
                url=metadata_url,
                caption="Execution Metadata",
                description=(
                    f"Variables: {', '.join(variables.keys())}"
                    if variables
                    else "Execution details"
                ),
                metadata=ToolArtifactMetadata(
                    duration=duration,
                    output_format="json",
                ),
            )
        )

        # Create the artifact
        artifact = ToolMediaArtifact(
            media_type="code",
            items=artifact_items,
        )
        return [artifact.model_dump()]

    async def _arun(
        self,
        python_code: str,
        config: RunnableConfig,
        stateful: bool = True,
    ) -> tuple[str, list]:
        try:
            start_time = time.perf_counter()

            # Create sandbox key for caching if stateful
            sandbox_key = f"stateful_{id(config)}" if stateful and config else None

            # Get or create sandbox
            if stateful and sandbox_key and sandbox_key in self._sandbox_cache:
                cached_data = self._sandbox_cache[sandbox_key]
                sandbox, session_bytes, session_metadata = cached_data
            else:
                sandbox = PyodideSandbox(allow_net=True)
                session_bytes = None
                session_metadata = None

            # Execute code
            result = await sandbox.execute(
                python_code,
                session_bytes=session_bytes,
                session_metadata=session_metadata,
            )

            # Cache session state if stateful
            if stateful and sandbox_key:
                self._sandbox_cache[sandbox_key] = (
                    sandbox,
                    result.session_bytes,
                    result.session_metadata,
                )

                # Cancel existing cleanup task if any
                if sandbox_key in self._cleanup_tasks:
                    self._cleanup_tasks[sandbox_key].cancel()

                # Schedule new cleanup in 15 minutes
                cleanup_task = asyncio.create_task(
                    self._schedule_cleanup(sandbox_key, delay=900)
                )
                self._cleanup_tasks[sandbox_key] = cleanup_task

            duration = time.perf_counter() - start_time

            # Extract output
            stdout = result.stdout or ""
            stderr = result.stderr or ""

            # Combine output
            output_parts = []
            if stdout:
                output_parts.append(f"Output:\n{stdout}")
            if stderr:
                output_parts.append(f"Warnings/Errors:\n{stderr}")

            combined_output = "\n\n".join(output_parts) if output_parts else "No output"

            # Create artifacts
            folder_name = f"pyodide_{uuid4().hex}"
            artifacts_folder = os.path.join(
                neuron_config.static_folder, "artifacts", folder_name
            )
            os.makedirs(artifacts_folder, exist_ok=True)

            # Prepare execution data
            execution_data = {
                "type": "pyodide_execution",
                "execution_time": duration,
                "stateful": stateful,
                "timestamp": time.time(),
            }

            if result.session_metadata and "variables" in result.session_metadata:
                variables = result.session_metadata["variables"]
                if variables:
                    execution_data["variables"] = variables

            # Write artifact files
            code_url, output_url, metadata_url = await self._write_artifact_files(
                python_code, stdout, stderr, execution_data, artifacts_folder
            )

            # Create artifacts
            execution_info = {
                "python_code": python_code,
                "stdout": stdout,
                "stderr": stderr,
                "duration": duration,
            }
            artifacts = await self._create_artifacts(
                execution_info,
                (code_url, output_url, metadata_url),
                execution_data,
                config,
            )

            logger.debug(f"Created Pyodide artifacts in {artifacts_folder}")

            # Format markdown output for LLM
            markdown_output = f"""{combined_output}

Execution time: {duration:.3f} seconds"""

            return markdown_output.strip(), artifacts

        except Exception as e:
            logger.error(f"Pyodide execution error: {e}", exc_info=True)
            return f"Error: {str(e)}", []

    async def cleanup(self) -> None:
        """Clean up resources on shutdown."""
        # Cancel all cleanup tasks
        for task in self._cleanup_tasks.values():
            task.cancel()
        self._cleanup_tasks.clear()
        self._sandbox_cache.clear()

    def __del__(self) -> None:
        """Cancel all cleanup tasks on tool destruction."""
        # Do synchronous cleanup only
        for task in self._cleanup_tasks.values():
            with suppress(RuntimeError):
                task.cancel()
        self._cleanup_tasks.clear()
        self._sandbox_cache.clear()
