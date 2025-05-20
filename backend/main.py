from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import sys
import os
import json
import io
from config import MAX_FUNCTION_CALL_DEPTH, OS_NAME, NOW
import json
from tools_state import tool_definitions, tool_functions
import threading
from watcher import start_file_watcher, load_tools
from uprint import MessageType, uprint

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Make sure .env file exists
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    uprint(".env file not found, creating one")
    env_path.touch()

load_dotenv()

# API key not found, prompt user for one
api_key = os.environ.get("OPENAI")
if not api_key:
    uprint("OPENAI not found in environment.")
    api_key = input("Please paste your OpenAI API key: ").strip()

    if not api_key:
        uprint("No API key provided. Exiting.")
        sys.exit(1)
    
    with open(env_path, "w") as f:
        f.write(f"OPENAI={api_key}")
    
    load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI"))

system_prompt = f"""
You are an intelligent, resourceful assistant with access to tools and memory. Your goal is to help the user accomplish tasks efficiently and independently, using available tools and your own reasoning.

You have access to the entire workspace, including:
- All files and directories (printed via the `directory_tree`), `read_file`, and `write_file` tools. This includes `main.py`, `config.py`, and the `tools/` directory.
- The `storage` directory contains persistent storage for some tools, such as a reminders and calendar json
- The `tools/` directory contains Python files defining callable tools. These tools are automatically injected into your API calls and can be used to perform actions such as file I/O, command execution, and web access.
- You may create new tools at any time by writing Python functions to files within the `tools/` directory. Each function must be decorated with `@tool("...")` and include a clear, descriptive string explaining its purpose.
- You must declare the **type of each parameter** in the function signature to ensure it is usable via the function calling interface. For example:

@tool("Generates a directory tree for the given path")
def directory_tree(path: str = ".", depth: int = 2):

### Guidelines:
- Think **autonomously**. Plan and execute multi-step tasks **without asking for permission** unless the action is risky.
- You are encouraged to **chain tool calls** to reach the user's intended goal. Don't stop early unless necessary.
- **Infer intent** from user messages and proactively take the next step.
- **Avoid asking the user to repeat themselves** if you can deduce their goal or continue from previous context.
- Only ask questions if something is truly ambiguous or needs clarification before continuing.
- Avoid repeating tool names in explanations unless requested. Focus on delivering the result.
- Before accessing or modifying the workspace, consider using `directory_tree` to list existing files.

### Constraints:
- Never delete, remove, overwrite, or modify the contents of: `main.py`, `config.py`, `tools_state.py`, `tool_decorator.py`, `watcher.py`, or `.env`.
- Use `execute_shell_command` **only when explicitly requested** or after clear confirmation.
- Move unwanted files to the `garbage/` directory instead of deleting them.
- If the user asks to delete or remove any files, move them to the `garbage/` directory.

### Environment:
- OS: {OS_NAME}
- Current datetime: {NOW}

Capabilities:
- Read/write files
- Execute tools
- Plan and carry out multi-step actions
"""

def chat():
    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    while True:
        payload = input()
        data = json.loads(payload)
        user_input = data[0]["payload"]

        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model = "gpt-4.1-mini",
            messages = messages,
            tools = tool_definitions,
            tool_choice = "auto"
        )

        msg = response.choices[0].message
        messages.append(msg)

        # keep looping while gpt decides to call a function
        times = 0
        while msg.tool_calls:
            if times > MAX_FUNCTION_CALL_DEPTH:
                messages.append({
                    "role": "system",
                    "content": f"Max function call depth reached ({MAX_FUNCTION_CALL_DEPTH}). Returning control back to the user."
                })
                uprint(f"\n Max function chaining limit reached ({MAX_FUNCTION_CALL_DEPTH}).\n")

                messages.append({
                    "role": "assistant",
                    "content": f"I've reached the maximum allowed number of tool calls in a row ({MAX_FUNCTION_CALL_DEPTH}). Requesting permission from user to continue."
                })
                break
            times = times + 1

            for call in msg.tool_calls:
                fn_name = call.function.name
                args = json.loads(call.function.arguments)
                formatted_args = ", ".join(repr(v) for v in args.values())

                uprint(f"{fn_name}({formatted_args})", MessageType.TOOL_CALL)

                if fn_name in tool_functions:
                    try:
                        result = tool_functions[fn_name](**args)
                    except Exception as e:
                        result =  f"An error occurred while calling '{fn_name}': {type(e).__name__}: {str(e)}"
                else:
                    result = f"Tool {fn_name} not found. Consider calling reload_tools_runtime"
                
                if not isinstance(result, str):
                    result = json.dumps(result, indent=2)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result
                })

                uprint(f"{fn_name}:{result}", MessageType.TOOL_RETURN)

            # Follow-up with results
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                tools = tool_definitions,
                tool_choice = "auto"
            )

            msg = response.choices[0].message
            messages.append(msg)
        else:
            uprint(msg.content)

import time

def background_announcer():
    count = 0
    while True:
        time.sleep(5)
        uprint(f"[Announcer] Ping {count}", MessageType.MESSAGE)
        count += 1

if __name__ == "__main__":
    load_tools()

    watcher_thread = threading.Thread(target=lambda: start_file_watcher(load_tools), daemon=True)
    watcher_thread.start()

    chat()