from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import importlib.util
import sys
from uprint import uprint
from state import tool_definitions, tool_functions

TOOLS_DIR = Path(__file__).parent / "tools"

def load_tools():
    tool_definitions.clear()
    tool_functions.clear()

    for file in TOOLS_DIR.glob("*.py"):
        module_name = file.stem

        # Ensure it's reloaded fresh
        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    
    return tool_definitions, tool_functions


class ToolChangeHandler(FileSystemEventHandler):
    def __init__(self, on_reload):
        self.on_reload = on_reload

    def on_any_event(self, event):
        if event.src_path.endswith(".py"):
            self.on_reload()


def start_file_watcher(on_reload):
    event_handler = ToolChangeHandler(on_reload)
    observer = Observer()
    observer.schedule(event_handler, str(TOOLS_DIR), recursive=False)
    observer.start()
    return observer
