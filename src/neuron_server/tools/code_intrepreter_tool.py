from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
from neuron_server.config import config
import os
from uuid import uuid4
import subprocess
import time


class CodeInterpreterToolArgs(BaseModel):
    python_code: str = Field(
        description="""
Python code to execute. Must be a valid python code string and must always include the data hard coded into the code. You may only write to the {directory} directory. Must be in utf-8 encoding. All variables must be defined. Use coding best practices. This is in a headless environment so do not use any GUI libraries. Print all outout to the stdout which is returned as the tool response. Use markdown formatting with math and katex support to make the stdout more readable. Double check your work. You must return something in the stdout. Do not use emojis. Do not use eval.

The following pip packages are available as needed:
adjustText
astroplan
astropy
kaleido
matplotlib
numpy
pandas
pillow
plotly
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


class CodeInterpreterTool(BaseTool):
    name: str = "code_interpreter"
    description: str = (
        """
This tool executes sandboxed Python code for complex data analysis, providing precise computational results for enhanced response generation. It leverages libraries such as pandas, numpy, scipy, and statsmodels for tasks like data cleaning, statistical modeling, and numerical computations. Use this for precise calculations and data analysis.
""".strip()
    )

    args_schema: Type[CodeInterpreterToolArgs] = CodeInterpreterToolArgs

    timeout: int = 60
    code_interpreter_image: str = "192.168.1.160:5000/code-interpreter:latest"

    def _run(self, description: str, python_code: str) -> str:
        return asyncio.run(self._arun(description, python_code))

    async def _arun(self, python_code: str) -> str:
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
                            "neuron-code-interpreter",
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
            if not process.stdout or len(process.stdout.strip()) == 0:
                raise Exception("No stdout")
            logger.debug(
                f"Code interpreter tool execution time: {time.perf_counter() - start_time:.2f} seconds"
            )
            return process.stdout.strip()
        except asyncio.TimeoutError:
            message = f"python code execution timed out after {self.timeout} seconds"
            logger.error(message)
            raise Exception(message)
        except Exception as e:
            logger.exception(e)
            raise e
