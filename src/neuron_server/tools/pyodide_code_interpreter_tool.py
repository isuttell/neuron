"""Pyodide-based code interpreter tool using LangChain Sandbox."""

import asyncio
import json
import time
from contextlib import suppress
from typing import Any

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from langchain_sandbox import PyodideSandbox
from pydantic import BaseModel, Field

from neuron_server.logger import logger
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

    async def _arun(
        self,
        python_code: str,
        stateful: bool = True,
        config: RunnableConfig | None = None,
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
                sandbox = PyodideSandbox(
                    allow_net=True,  # Allow network access for data fetching
                )
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

            # Create artifacts from any returned data
            artifacts = []

            # If there's structured output or data, create a data artifact
            if result.session_metadata and "variables" in result.session_metadata:
                variables = result.session_metadata["variables"]
                if variables:
                    # Create a simple data artifact with variable info
                    artifact_data = {
                        "type": "variables",
                        "data": variables,
                        "execution_time": duration,
                    }

                    artifact = ToolMediaArtifact(
                        media_type="data",
                        items=[
                            ToolMediaItem(
                                id="pyodide_variables",
                                url="data:application/json;base64,"
                                + json.dumps(artifact_data).encode().hex(),
                                caption="Execution Variables",
                                description=(
                                    f"Variables: {', '.join(variables.keys())}"
                                ),
                                metadata=ToolArtifactMetadata(
                                    duration=duration, output_format="json"
                                ),
                            )
                        ],
                    )
                    artifacts.append(artifact.model_dump())

            # Format markdown output
            files_section = ""
            if artifacts:
                artifact_obj = ToolMediaArtifact(**artifacts[0])
                files_section = artifact_obj.to_xml()
            else:
                files_section = "No structured data generated"

            markdown_output = f"""# Pyodide Code Interpreter Results

## Output

```
{combined_output}
```

## Data

{files_section}

## Execution Time

{duration:.3f} seconds (WebAssembly)"""

            return markdown_output.strip(), artifacts

        except Exception as e:
            logger.error(f"Pyodide execution error: {e}", exc_info=True)

            # Return error as markdown
            error_output = f"""# Pyodide Code Interpreter Error

## Error Details

```
{str(e)}
```

The code execution failed. Common issues:
- Package not available in Pyodide environment
- Syntax errors in Python code
- Attempts to access file system (not supported)
- Memory limitations in WebAssembly

Try simplifying the code or using the Docker-based code_interpreter tool
for complex operations."""

            return error_output.strip(), []

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
