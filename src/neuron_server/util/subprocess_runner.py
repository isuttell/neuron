import asyncio
import subprocess
from typing import List, Tuple, Optional
from neuron_server.logger import logger


async def run_subprocess(
    args: List[str],
    timeout: Optional[int] = None,
    check: bool = True,
    **kwargs,
) -> subprocess.CompletedProcess[str]:
    """
    Run a subprocess asynchronously optionally with timeout.

    Args:
        args: List of command arguments
        timeout: Timeout in seconds
        check: Whether to raise an exception on non-zero return code
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        CompletedProcess instance

    Raises:
        asyncio.TimeoutError: If process exceeds timeout
        subprocess.CalledProcessError: If check=True and process returns non-zero
    """
    loop = asyncio.get_running_loop()
    logger.info(f"Running: {' '.join(args)}")

    run_process = lambda: subprocess.run(args, **kwargs)

    if timeout:
        process: subprocess.CompletedProcess[str] = await asyncio.wait_for(
            loop.run_in_executor(None, run_process),
            timeout=timeout,
        )
    else:
        process: subprocess.CompletedProcess[str] = await loop.run_in_executor(
            None,
            run_process,
        )

    if check and process.returncode != 0:
        raise subprocess.CalledProcessError(
            process.returncode,
            args,
            process.stdout,
            process.stderr,
        )

    return process
