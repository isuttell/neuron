import asyncio
import sys
from asyncio import create_subprocess_exec, create_subprocess_shell
from asyncio.subprocess import PIPE


class CommandRunner:
    def __init__(self) -> None:
        if sys.platform == "win32":
            # Set the policy for Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def run_command(
        self, command: str | list[str], shell: bool = False
    ) -> tuple[int, str, str]:
        """
        Run a command and return its output

        Args:
            command: Either a string (for shell=True) or list of arguments
            shell: Whether to run command through shell

        Returns:
            tuple: (return_code, stdout, stderr)
        """
        try:
            if shell:
                process = await create_subprocess_shell(
                    command, stdout=PIPE, stderr=PIPE
                )
            else:
                process = await create_subprocess_exec(
                    *command, stdout=PIPE, stderr=PIPE
                )

            stdout, stderr = await process.communicate()
            return process.returncode, stdout.decode(), stderr.decode()

        except Exception as e:
            return -1, "", str(e)

    async def run_with_timeout(
        self, command: str | list[str], timeout: int = 60, shell: bool = False
    ) -> tuple[int, str, str]:
        """
        Run a command with a timeout

        Args:
            command: The command to run
            timeout: Timeout in seconds
            shell: Whether to run command through shell

        Returns:
            tuple: (return_code, stdout, stderr)
        """
        try:
            return await asyncio.wait_for(
                self.run_command(command, shell), timeout=timeout
            )
        except TimeoutError:
            return -1, "", "Command timed out"
