from config import BASE_PATH
from pathlib import Path
from tool_decorator import tool

@tool("Writes content to a file at the given path")
def write_file(path:str, content:str):
    try:
        file_path = BASE_PATH / Path(path)
        with file_path.open('w') as f:
            f.write(content)
        return "File written successfully."
    except Exception as e:
        return f"Error writing file: {e}"