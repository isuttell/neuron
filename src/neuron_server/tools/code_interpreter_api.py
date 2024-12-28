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
import shutil
from typing import List


class RestrictedKeywordError(Exception):
    def __init__(self, message: str, excerpt: str):
        self.message = message
        self.excerpt = excerpt
        super().__init__(self.message)

    def __str__(self):
        return f"RestrictedKeywordError: {self.message}\nExcerpt:\n{self.excerpt}"


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
        "exec(",
        "eval(",
        "compile(",
        "execfile(",
        "os.popen(",
        "os.spawn(",
        "os.fork(",
        "__import__",
        "input(",
        "os.environ",
    ]

    lines = python_code.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for keyword in restricted_keywords:
            if keyword in line:
                excerpt = "\n".join(lines[line_number - 3 : line_number + 3])
                raise RestrictedKeywordError(
                    f'Unable to run code due to restricted keyword: "{keyword}" on line {line_number}. Refactor your code to remove this keyword and try again.',
                    excerpt,
                )


def get_media_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1]
    if ext in [
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
    ]:
        return "image"
    elif ext in [
        ".mp4",
        ".mov",
        ".webm",
    ]:
        return "video"
    elif ext in [
        ".mp3",
        ".wav",
        ".ogg",
    ]:
        return "audio"
    elif ext in [
        ".html",
        ".htm",
    ]:
        return "html"
    elif ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
        return "code"
    elif ext in [
        ".pdf",
        ".csv",
        ".txt",
        ".json",
        ".md",
    ]:
        return "data"
    logger.warning(f"Unknown file extension: {ext}")
    return "unknown"


def force_stop_code_interpreter():
    subprocess.run(
        ["docker", "rm", "-v", "-f", "neuron-code-interpreter"],
    )


async def run_code_interpreter(
    python_code: str,
    timeout: int = 120,
    code_interpreter_image: str = "192.168.1.160:5000/code-interpreter:latest",
    cpu_limit: int = 16,
    memory_limit: int | str = "16g",
):
    try:
        start_time = time.perf_counter()
        check_for_restricted_keywords(python_code)
        script_filename = "main.py"
        folder_name = uuid4().hex
        temp_folder = os.path.join(config.temp_folder, folder_name)
        artifacts_folder = os.path.join(
            config.static_folder,
            "artifacts",
            folder_name,
        )
        os.makedirs(os.path.join(temp_folder, "artifacts"))
        script_file = os.path.join(temp_folder, script_filename)
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(python_code)
        logger.info(f"Saved python code to {script_file} and executing...")
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
                        f"{memory_limit}",
                        "--cpus",
                        f"{cpu_limit}",
                        "--read-only",
                        "--rm",
                        "--cap-drop",
                        "ALL",
                        "--user",
                        "nobody",
                        "--network=none",
                        "-v",
                        "tmpfs:/tmp",
                        "-v",
                        f"{temp_folder}:/app",
                        code_interpreter_image,
                        script_filename,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                ),
            ),
            timeout=timeout,
        )
        duration = time.perf_counter() - start_time
        if process.returncode != 0:
            raise Exception(f"Error executing script: stderr={process.stderr.strip()}")
        logger.info(f"Code interpreter tool execution time: {duration:.2f} seconds")
        temp_artifacts_folder = os.path.join(temp_folder, "artifacts")
        shutil.copytree(
            temp_artifacts_folder,
            artifacts_folder,
        )

        artifacts: List[str] = []

        # Copy the source code to the artifacts folder
        src_filename = "source_code.py"
        src_file = os.path.join(artifacts_folder, src_filename)
        shutil.copy(script_file, artifacts_folder)
        os.rename(os.path.join(artifacts_folder, script_filename), src_file)

        if process.stdout:
            stdout_filename = "stdout.md"
            stdout_file = os.path.join(artifacts_folder, stdout_filename)
            with open(stdout_file, "w", encoding="utf-8") as f:
                f.write(process.stdout.strip())

        for file in os.listdir(artifacts_folder):
            media_type = get_media_type(file)
            if media_type == "unknown":
                continue
            url = f"{config.static_content_url}/artifacts/{folder_name}/{file}"
            if media_type == "image":
                artifacts.append(f"![{file}]({url})")
            elif media_type == "video":
                artifacts.append(f'<video src="{url}" controls />')
            elif media_type == "audio":
                artifacts.append(f'<audio src="{url}" controls />')
            else:
                artifacts.append(f"[{file}]({url})")
        return process.stdout.strip() if process.stdout else "", artifacts
    except asyncio.TimeoutError:
        force_stop_code_interpreter()
        raise Exception(f"python code execution timed out after {timeout} seconds")
