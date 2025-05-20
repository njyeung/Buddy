import os
from config import BASE_PATH
from tool_decorator import tool

EXCLUDE_DIRS = {"node_modules", ".git", "dist", "__pycache__"}

@tool("Returns a tree view of a directory up to a given depth")
def directory_tree(path:str=".", depth:int=3):
    base_path = BASE_PATH / path
    if not base_path.exists():
        return f"Path '{base_path}' does not exist."

    tree_lines = []

    def walk(dir_path, prefix="", level=0):
        if level > depth:
            return

        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            return

        entries = [e for e in entries if e not in EXCLUDE_DIRS]

        for i, entry in enumerate(entries):
            full_path = os.path.join(dir_path, entry)
            is_last = i == len(entries) - 1
            connector = "\- " if is_last else "|- "

            tree_lines.append(f"{prefix}{connector}{entry}")

            if os.path.isdir(full_path):
                extension = "   " if is_last else "|  "
                walk(full_path, prefix + extension, level + 1)

    # Check if base path itself is excluded
    root_name = base_path.name
    if root_name not in EXCLUDE_DIRS:
        tree_lines.append(root_name)
        walk(str(base_path.resolve()), "", 1)
    else:
        return f"Path '{base_path}' is excluded."

    return "\n".join(tree_lines)
