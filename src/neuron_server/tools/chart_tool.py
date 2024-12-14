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
import sys


class ChartToolArgs(BaseModel):
    description: str = Field(
        description="The description of the chart. This will be displayed in the markdown link to the chart."
    )
    python_code: str = Field(
        description="""
Python code to generate a chart. Must be a valid python code string and always include the data hard coded in the code. The code must save the plot to a file in the {directory} folder with the name 'chart.png'. By default when using matplotlib use the 'dark_background' style. Save the plot with a transparent background as this shows best in the interface by default and use text colors that work on dark backgrounds. Must be in utf-8 encoding. All variables must be defined. Use coding best practices. Stdout is returned so use it to return any additional information to the user. This is in a headless environment so do not use any GUI libraries.

The following pip packages are installed and available to use when needed:
numpy
matplotlib
pandas
seaborn[stats]
scipy
statsmodels
scienceplots
adjustText
plotnine[all]
""".format(
            directory="/app"
        ).strip()
    )


class ChartTool(BaseTool):
    name: str = "chart"
    description: str = (
        """
This tool allows you to do data analysis and generate visualizations using python. Use this tool to help visualize data or when the user asks for a chart/plot.

Guidelines:
- Use NumPy, SciPy, and Statsmodels for complex math/stats
- Use Matplotlib, Seaborn, and Plotnine for customized, visually rich charts
- Returns a markdown link to the chart to show the user
- Returns stdout from the python code execution
- Charts should be print publication quality
- Ensure labels are readable and do not overlap with other elements
- Do not make them visualizations interactive or animated. They must be static.
- When using the "science" style, import scienceplots first
""".strip()
    )

    args_schema: Type[ChartToolArgs] = ChartToolArgs

    code_interpreter_image: str = "192.168.1.160:5000/code-interpreter:latest"

    def _run(self, description: str, python_code: str) -> str:
        return asyncio.run(self._arun(description, python_code))

    async def _arun(self, description: str, python_code: str) -> str:
        try:
            start_time = time.perf_counter()
            script_filename = "main.py"
            temp_folder = os.path.join(config.temp_folder, uuid4().hex)
            os.makedirs(temp_folder)
            script_file = os.path.join(temp_folder, script_filename)
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(python_code)
            logger.info(f"Saved python code to {script_file}")
            loop = asyncio.get_running_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [
                        "docker",
                        "run",
                        "--name",
                        "neuron-chart",
                        "--rm",
                        "-v",
                        f"{temp_folder}:/app",
                        self.code_interpreter_image,
                        script_filename,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ),
            )
            if process.returncode != 0:
                raise Exception(
                    f"Error executing script: stderr={process.stderr.strip()}"
                )
            output_filename = os.path.join(temp_folder, "chart.png")
            if not os.path.exists(output_filename):
                raise Exception("chart.png not found")
            result_filename = f"chart_{uuid4().hex}.png"
            result_file_path = os.path.join(
                config.static_folder, "images", result_filename
            )
            os.rename(output_filename, result_file_path)
            url = f"{config.static_content_url}/images/{result_filename}"
            logger.debug(
                f"Saved plot to {result_file_path} <{url}> in {time.perf_counter() - start_time:.2f} seconds"
            )
            return f"![{description}]({url})\n{process.stdout.strip()}"
        except Exception as e:
            logger.exception(e)
            raise e
