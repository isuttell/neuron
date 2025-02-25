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


async def setup_execution_environment(
    python_code: str,
    folder_name: str,
) -> tuple[str, str, str]:
    """Set up the execution environment and save the code."""
    script_filename = "main.py"
    temp_folder = os.path.abspath(os.path.join(neuron_config.temp_folder, folder_name))
    temp_artifacts_folder = os.path.join(temp_folder, "artifacts")
    os.makedirs(temp_artifacts_folder, mode=0o755)
    script_file = os.path.join(temp_folder, script_filename)

    with open(script_file, "w", encoding="utf-8") as f:
        f.write(python_code)

    logger.info(f"Saved python code to {script_file} and executing...")
    return script_file, temp_artifacts_folder, script_filename


def get_docker_args(
    folder_name: str,
    memory_limit: str,
    cpu_limit: int,
    script_filename: str,
    code_interpreter_image: str,
) -> list[str]:
    """Construct Docker run command arguments."""
    docker_folder_reference = os.path.abspath(
        os.path.join(neuron_config.parent_temp_folder, folder_name)
    )
    return [
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
        "--network=none",
        "-v",
        "tmpfs:/tmp",
        "-v",
        f"{docker_folder_reference}:/app",
        code_interpreter_image,
        script_filename,
    ]


async def process_artifacts(
    folder_name: str,
    temp_artifacts_folder: str,
    script_file: str,
    process_output: str,
    config: RunnableConfig,
) -> tuple[str, list[str]]:
    """Process execution artifacts and generate media items."""
    artifacts_folder = os.path.join(
        neuron_config.static_folder, "artifacts", folder_name
    )
    shutil.copytree(temp_artifacts_folder, artifacts_folder)
    artifacts: list[str] = []

    # Copy source code
    src_filename = "source_code.py"
    src_file = os.path.join(artifacts_folder, src_filename)
    shutil.copy(script_file, artifacts_folder)
    os.rename(os.path.join(artifacts_folder, "main.py"), src_file)

    # Save stdout
    if process_output:
        stdout_file = os.path.join(artifacts_folder, "stdout.md")
        with open(stdout_file, "w", encoding="utf-8") as f:
            f.write(process_output.strip())

    # Process generated files
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
        logger.debug(f"Artifact created <{url}>")

    return process_output.strip() if process_output else "", artifacts


async def run_code_interpreter(
    python_code: str,
    timeout: int = 120,
    code_interpreter_image: str = "gitea.zaks.io/isuttell/code-interpreter:latest",
    config: RunnableConfig = None,
) -> tuple[str, list[str]]:
    """Execute Python code in a sandboxed environment and process the results."""
    try:
        cpu_limit = config.get("cpu_limit", 16) if config else 16
        memory_limit = config.get("memory_limit", "16g") if config else "16g"
        start_time = time.perf_counter()

        check_for_restricted_keywords(python_code)
        folder_name = uuid4().hex
        (
            script_file,
            temp_artifacts_folder,
            script_filename,
        ) = await setup_execution_environment(python_code, folder_name)

        args = get_docker_args(
            folder_name,
            memory_limit,
            cpu_limit,
            script_filename,
            code_interpreter_image,
        )

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

        return await process_artifacts(
            folder_name,
            temp_artifacts_folder,
            script_file,
            process.stdout,
            config,
        )

    except TimeoutError:
        await force_stop_code_interpreter()
        raise Exception(
            f"python code execution timed out after {timeout} seconds"
        ) from None
