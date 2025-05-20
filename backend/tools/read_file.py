from config import BASE_PATH
from pathlib import Path

from tool_decorator import tool

@tool("Reads the content of a file")
def read_file(path:str):
    try:
        file_path = BASE_PATH / Path(path)
        with file_path.open("r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"