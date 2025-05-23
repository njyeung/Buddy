from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import sys
import os
import json
import io
from config import MAX_FUNCTION_CALL_DEPTH, OS_NAME, NOW
import json
from state import tool_definitions, tool_functions
import threading
from watcher import start_file_watcher, load_tools
from uprint import OutGoingDataType, uprint
from storage.chat_storage import init_db, create_chat, insert_message, get_chat_messages, get_latest_chat_id, get_chats
import state

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

def handle_tool_calls(messages, msg, chat_id):
    times = 0
    while msg.tool_calls:
        if times > MAX_FUNCTION_CALL_DEPTH:
            limit_msg = f"Max function call depth reached ({MAX_FUNCTION_CALL_DEPTH}). Returning control back to the user."
            messages.append({"role": "tool", "content": limit_msg})
            insert_message(chat_id, "tool", limit_msg)
            uprint(limit_msg, OutGoingDataType.TOOL_RETURN)

            messages.append({"role": "assistant", "content": "I've reached the maximum allowed number of tool calls. Requesting permission to continue."})
            insert_message(chat_id, "assistant", "I've reached the maximum allowed number of tool calls. Requesting permission to continue.")
            return

        for call in msg.tool_calls:
            fn_name = call.function.name
            args = json.loads(call.function.arguments)
            uprint(f"{fn_name}({', '.join(repr(v) for v in args.values())})", OutGoingDataType.TOOL_CALL)

            result = tool_functions.get(fn_name, lambda **_: f"Tool {fn_name} not found.")(**args)
            if not isinstance(result, str):
                result = json.dumps(result, indent=2)

            tool_msg = {"role": "tool", "tool_call_id": call.id, "content": result}
            messages.append(tool_msg)
            insert_message(chat_id, "assistant", f"tool-call: {fn_name}({', '.join(repr(v) for v in args.values())}), tool-return: {result}")
            uprint(f"{fn_name}: {result}", OutGoingDataType.TOOL_RETURN)

        # Follow up after tool execution
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=tool_definitions,
            tool_choice="auto"
        )
        msg = response.choices[0].message
        messages.append(msg)
        uprint(msg.content)
        insert_message(chat_id, "assistant", msg.content)
        times += 1

def chat():
    init_db()
    state.current_chat_id = get_latest_chat_id()
    messages = get_chat_messages(state.current_chat_id)
        
    if not messages:
        system_msg = {"role": "system", "content": system_prompt}
        messages.append(system_msg)
        insert_message(state.current_chat_id, "system", system_prompt)

    while True:
        data = json.loads(input())
        data = data[0]
        type = data['type']
        payload = data['payload']

        if type == "switch-chat":
            # Used to create a new chat
            if payload is None:
                state.current_chat_id = create_chat("new chat")
                messages = get_chat_messages(state.current_chat_id)
                system_msg = {"role": "system", "content": system_prompt}
                messages.append(system_msg)
                insert_message(state.current_chat_id, "system", system_prompt)

                chats = get_chats()
                for chat in chats:
                    chat["active"] = (chat["id"] == state.current_chat_id)
                uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)
            # Switch to an existing chat and return all messages from that chat
            else:
                try:
                    new_id = int(payload)
                    uprint(f"Switching to chat ID {new_id}", OutGoingDataType.LOG)
                    state.current_chat_id = new_id
                    messages = get_chat_messages(state.current_chat_id)
                    if not messages:
                        system_msg = {"role": "system", "content": system_prompt}
                        messages.append(system_msg)
                        insert_message(state.current_chat_id, "system", system_prompt)
                    uprint(messages, OutGoingDataType.RETURN_CHAT_MESSAGES)
                    uprint(state.current_chat_id, OutGoingDataType.RETURN_CURRENT_CHAT_ID)
                except ValueError:
                    uprint(f"Invalid chat ID: {payload}", OutGoingDataType.LOG)
            continue
        if type == "get-all-chats":
            chats = get_chats()
            for chat in chats:
                chat["active"] = (chat["id"] == state.current_chat_id)
            uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)
            continue
        if type == "get-current-chat-id":
            uprint(state.current_chat_id, OutGoingDataType.RETURN_CURRENT_CHAT_ID)
        if type == "get-chat-messages":
            uprint(messages, OutGoingDataType.RETURN_CHAT_MESSAGES)
        
        if type != "user-message":
            continue

        messages.append({"role": "user", "content": payload})
        insert_message(state.current_chat_id, "user", payload)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=tool_definitions,
            tool_choice="auto"
        )

        msg = response.choices[0].message
        messages.append(msg)
        insert_message(state.current_chat_id, msg.role, msg.content)

        if msg.tool_calls:
            handle_tool_calls(messages, msg, state.current_chat_id)
        else:
            uprint(msg.content)

if __name__ == "__main__":
    load_tools()
    threading.Thread(target=lambda: start_file_watcher(load_tools), daemon=True).start()
    chat()