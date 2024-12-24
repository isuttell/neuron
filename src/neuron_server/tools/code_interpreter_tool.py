from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
import time
from neuron_server.tools.code_interpreter_api import run_code_interpreter


class CodeInterpreterToolArgs(BaseModel):
    python_code: str = Field(
        description="""
Professional quality python 3.12 code which is saved to a file and executed. Must be valid self contained python code and must always include the inputs/data hard coded. You may only write to the {directory} directory. Must be in utf-8 encoding. All variables must be defined. Use coding best practices. Network requests are blocked. This is in a headless environment so do not use any GUI libraries or methods like plt.show(). This does not support interactivity. Results must be saved to the {directory}/artifacts/ directory. Print answer to the stdout which is returned as the tool response. Show your work and work step by step. When writing Latex ensure its clean and valid. You must return something in the stdout. Do not use emojis. Never use exec, eval or input. When using the science style import scienceplots first before using the style to ensure it is available.

These are the only pip modules installed and available:
adjustText
astroplan
astropy
kaleido
matplotlib
numpy
opencv-python-headless
pandas
pillow
plotly
plotnine[all]
scienceplots
scipy
seaborn[stats]
statsmodels

Only the following ephemeris data is available for astropy:
de405
de430t
""".format(
            directory="/app"
        ).strip()
    )


class CodeInterpreterTool(BaseTool):
    name: str = "code_interpreter"
    description: str = (
        """
This tool executes Python code in a restricted headless environment for data analysis, precise computations, graphing, and visualizations for enhanced response generation. It leverages libraries such as pandas, numpy, scipy, and statsmodels for tasks like data cleaning, statistical modeling, and numerical computations. It also uses Matplotlib, Seaborn, Plotnine, and Plotly for customized, visually rich charts. Use this for precise calculations, data analysis, and data visualizations.

The code is executed in a sandboxed, headless, noninteractive environment with no internet access. Use of eval and exec is also blocked. Code must complete within 120 seconds.
""".strip()
    )

    args_schema: Type[CodeInterpreterToolArgs] = CodeInterpreterToolArgs

    timeout: int = 120
    code_interpreter_image: str = "192.168.1.160:5000/code-interpreter:latest"

    def _run(self, description: str, python_code: str) -> str:
        return asyncio.run(self._arun(description, python_code))

    async def _arun(self, python_code: str) -> str:
        try:
            start_time = time.perf_counter()
            stdout, artifacts = await run_code_interpreter(
                python_code,
                code_interpreter_image=self.code_interpreter_image,
                timeout=self.timeout,
            )
            duration = time.perf_counter() - start_time
            artifacts_str = (
                "\n".join([f"* {artifact}" for artifact in artifacts])
                if len(artifacts) > 0
                else "No files"
            )
            return """
# Code Interpreter Results

## stdout

```
{stdout}
```

## Files

{artifacts}

## Execution Time

{duration:.2f} seconds
""".format(
                stdout=stdout if stdout else "No output",
                artifacts=artifacts_str,
                duration=duration,
            ).strip()
        except Exception as e:
            logger.exception(e)
            raise e
