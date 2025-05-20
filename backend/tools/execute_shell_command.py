import subprocess
import os
from config import BASE_PATH
from tool_decorator import tool

@tool("Executes a shell command")
def execute_shell_command(command: str):
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(BASE_PATH),
            capture_output=True,
            text=True
        )

        return result.stdout.strip() if result.stdout else result.stderr.strip()
    except Exception as e:
        return f"Error running shell command: {e}"