from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
import time
from neuron_server.config import config
import os
from uuid import uuid4
import subprocess
import shutil


class ChartToolArgs(BaseModel):
    description: str = Field(
        description="The description of the chart. This will be displayed in the markdown link to the chart."
    )
    python_code: str = Field(
        description="""
Python code to generate a chart. Must be a valid python code string and always include the data hard coded in the code. You may only write to the  {directory} directory. Save results as "{directory}/chart.png". Must be in utf-8 encoding. All variables must be defined. Use coding best practices. Stdout is returned so use it to return any information to the user in markdown. This is in a headless environment so do not use any GUI libraries. Latex is not installed so do not use it.

These are the only pip modules installed and available:
adjustText
astroplan
astropy
matplotlib
numpy
pandas
plotnine[all]
scienceplots
scipy
seaborn[stats]
starplot
statsmodels
""".format(
            directory="/app"
        ).strip()
    )


def check_for_restricted_keywords(python_code: str) -> None:
    restricted_keywords = [
        "/proc",
        "/sys",
        "/etc",
        "/var",
        "/root",
        "/home",
        "os.system",
        "subprocess",
        "shutil",
        "currentframe()",
        "open(",
        "socket",
        "requests",
        "http",
        "ftp",
        "exec",
        "eval",
        "compile",
        "execfile",
        "os.popen",
        "os.exec",
        "os.spawn",
        "os.fork",
        "__import__",
        "input",
        "os.environ",
    ]

    for keyword in restricted_keywords:
        if keyword in python_code:
            raise ValueError(
                f"The provided Python code contains restricted keyword: {keyword}"
            )


class ChartTool(BaseTool):
    name: str = "chart"
    description: str = (
        """
This tool allows you to do data analysis and generate visualizations using python. Use this tool to help visualize data or when the user asks for a chart/plot.

Guidelines:
- Use NumPy, SciPy, and Statsmodels for complex math/stats
- Use Matplotlib, Seaborn, and Plotnine for customized, visually rich charts. Prefer seaborn or Plotnine.
- Returns a markdown link to the chart to show the user
- Returns stdout from the python code execution
- Charts should be print publication quality
- Do not make visualizations interactive. Must return a png
- When using the "science" style, import scienceplots first
- The UI is dark so pick dark mode friendly colors by default
""".strip()
    )

    args_schema: Type[ChartToolArgs] = ChartToolArgs

    timeout: int = 60
    code_interpreter_image: str = "192.168.1.160:5000/code-interpreter:latest"

    def _run(self, description: str, python_code: str) -> str:
        return asyncio.run(self._arun(description, python_code))

    async def _arun(self, description: str, python_code: str) -> str:
        try:
            start_time = time.perf_counter()
            check_for_restricted_keywords(python_code)
            script_filename = "main.py"
            temp_folder = os.path.join(config.temp_folder, uuid4().hex)
            os.makedirs(temp_folder)
            script_file = os.path.join(temp_folder, script_filename)
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(python_code)
            logger.info(f"Saved python code to {script_file}")
            loop = asyncio.get_running_loop()
            process = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        [
                            "docker",
                            "run",
                            "--name",
                            "neuron-chart",
                            "--memory",
                            "4g",
                            "--cpus",
                            "8",
                            "--read-only",
                            "--rm",
                            "--cap-drop",
                            "ALL",
                            "--user",
                            "nobody",
                            "--network=none",
                            "-v",
                            f"{temp_folder}:/app",
                            self.code_interpreter_image,
                            script_filename,
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                    ),
                ),
                timeout=self.timeout,
            )

            if process.returncode != 0:
                raise Exception(
                    f"Error executing script: stderr={process.stderr.strip()}"
                )
            output_filename = os.path.join(temp_folder, "chart.png")
            if not os.path.exists(output_filename):
                raise Exception("chart.png not found")
            result_filename = f"chart_{uuid4().hex}.png"
            result_file_path = os.path.abspath(
                os.path.join(config.static_folder, result_filename)
            )
            shutil.move(output_filename, result_file_path)
            url = f"{config.static_content_url}/{result_filename}"
            logger.debug(
                f"Saved chart to {result_file_path} <{url}> in {time.perf_counter() - start_time:.2f} seconds"
            )
            return f"![{description}]({url})\n{process.stdout.strip() if process.stdout else ''}".strip()
        except asyncio.TimeoutError:
            message = f"python code execution timed out after {self.timeout} seconds"
            logger.error(message)
            raise Exception(message)
        except Exception as e:
            logger.exception(e)
            raise e
