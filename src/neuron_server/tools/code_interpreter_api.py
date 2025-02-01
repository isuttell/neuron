import os
import shutil
import subprocess
import time
from uuid import uuid4

from langchain_core.runnables import RunnableConfig

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.image_utilities import create_thumbnails
from neuron_server.util.subprocess_runner import run_subprocess


class RestrictedKeywordError(Exception):
    def __init__(self, message: str, excerpt: str) -> None:
        self.message = message
        self.excerpt = excerpt
        super().__init__(self.message)

    def __str__(self) -> str:
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
                    f'Unable to run code due to restricted keyword: "{keyword}" '
                    f"on line {line_number}.\n"
                    f"Refactor your code to remove this keyword and try again.\n"
                    f"{excerpt}"
                )


def get_media_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1]
    media_type = None
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
        media_type = "image"
    elif ext in [".mp4", ".mov", ".webm"]:
        media_type = "video"
    elif ext in [".mp3", ".wav", ".ogg"]:
        media_type = "audio"
    elif ext in [".html", ".htm"]:
        media_type = "html"
    elif ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
        media_type = "code"
    elif ext in [".pdf", ".csv", ".txt", ".json", ".md"]:
        media_type = "data"
    if media_type is None:
        logger.warning(f"Unknown file extension: {ext}")
        media_type = "unknown"
    return media_type


async def force_stop_code_interpreter() -> None:
    await run_subprocess(
        ["docker", "rm", "-v", "-f", "neuron-code-interpreter"],
    )


async def run_code_interpreter(
    python_code: str,
    timeout: int = 120,
    code_interpreter_image: str = "192.168.1.160:5000/code-interpreter:latest",
    config: RunnableConfig = None,
) -> tuple[str, list[str]]:
    try:
        cpu_limit = config.get("cpu_limit", 16) if config else 16
        memory_limit = config.get("memory_limit", "16g") if config else "16g"
        start_time = time.perf_counter()
        check_for_restricted_keywords(python_code)
        script_filename = "main.py"
        folder_name = uuid4().hex
        temp_folder = os.path.abspath(
            os.path.join(neuron_config.temp_folder, folder_name)
        )
        temp_artifacts_folder = os.path.join(temp_folder, "artifacts")
        os.makedirs(temp_artifacts_folder, mode=0o755)
        script_file = os.path.join(temp_folder, script_filename)
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(python_code)
        logger.info(f"Saved python code to {script_file} and executing...")
        # This needs to point to the host's filesystem and not the container's
        docker_folder_reference = os.path.abspath(
            os.path.join(neuron_config.parent_temp_folder, folder_name)
        )
        args = [
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
            # "--user",
            # "nobody",
            "--network=none",
            "-v",
            "tmpfs:/tmp",
            "-v",
            f"{docker_folder_reference}:/app",
            code_interpreter_image,
            script_filename,
        ]
        process = await run_subprocess(
            args=args,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        duration = time.perf_counter() - start_time
        if process.returncode != 0:
            raise Exception(f"Error executing script: stderr={process.stderr.strip()}")
        logger.info(f"Code interpreter tool execution time: {duration:.2f}s")

        artifacts_folder = os.path.join(
            neuron_config.static_folder,
            "artifacts",
            folder_name,
        )
        shutil.copytree(
            temp_artifacts_folder,
            artifacts_folder,
        )
        artifacts: list[str] = []

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
            url = f"{neuron_config.static_content_url}/artifacts/{folder_name}/{file}"
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type=media_type,
                user_id=config["configurable"].get("user_id"),
                thread_id=config["configurable"].get("thread_id"),
                name=file,
            )
            await MediaItemModel.create(create_params)
            if media_type == "image":
                artifacts.append(f"<image>![{file}]({url})</image>")
                create_thumbnails(os.path.join(artifacts_folder, file))
            elif media_type == "video":
                artifacts.append(f'<video src="{url}" controls />')
            elif media_type == "audio":
                artifacts.append(f'<audio src="{url}" controls />')
            else:
                artifacts.append(f"<link>[{file}]({url})</link>")
        return process.stdout.strip() if process.stdout else "", artifacts
    except TimeoutError:
        await force_stop_code_interpreter()
        raise Exception(
            f"python code execution timed out after {timeout} seconds"
        ) from None
