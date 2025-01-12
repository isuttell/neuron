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
Must be valid, fully self contained Python 3.12 code encoded in ascii. Must include all required data in the code. Use best practices. Network requests are blocked. This is in a headless environment so do not use any GUI methods like plt.show(). You may only write to the {directory} directory. Results must be saved to the {directory}/artifacts/ directory. Print answer to the stdout with markdown formatting which is returned as the tool response. Show/print your work step by step. Do not use emojis. Never use the following methods: open, exec, eval. When using the matplot styles like the science or seaborn styles import the associated library, e.g. scienceplots first before using the style. ffmpeg is installed.

Installed Modules:

astroplan==0.10.1
astropy==7.0.0
kaleido==0.2.1
matplotlib==3.10.0
numpy==2.2.1
opencv-python-headless==4.10.0.84
pandas==2.2.3
pillow==11.0.0
plotly==5.24.1
scienceplots==2.1.1
scipy==1.14.1
seaborn[stats]==0.13.2
statsmodels==0.14.4

Available ephemeris data:

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
This tool executes Python code in a restricted environment for data analysis, precise computations, graphing, and visualizations for enhanced response generation. It leverages libraries such as pandas, numpy, scipy, and statsmodels for tasks like data cleaning, statistical modeling, and numerical computations. It also uses Matplotlib, Seaborn, and Plotly for customized, visually rich charts. Use this for precise calculations, data analysis, and data visualizations. The code is executed in a sandboxed, headless, noninteractive environment with no internet access. Use of eval, exec, and input is blocked. Code must complete within 300 seconds.
""".strip()
    )

    args_schema: Type[CodeInterpreterToolArgs] = CodeInterpreterToolArgs

    timeout: int = 300
    code_interpreter_image: str = "192.168.1.160:5000/code-interpreter:latest"

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

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
            logger.error(e, exc_info=True)
            raise e
