from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import sys
import os
import json
import io
from config import MAX_FUNCTION_CALL_DEPTH, NUM_RECENT_MESSAGES_TO_KEEP, OS_NAME, NOW, SUMMARY_TRIGGER_CHAR_COUNT
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



def summarize_messages(client: OpenAI, chat_id: int):
    # Strip system prompts and keep last N messages

    # Context layout:
    # Initial system prompt
    # Dynamic summary system prompt (if present)    ]   We are taking care of this section here 
    # Earlier messages (to be summarized)           ]
    # Most recent X messages                        ]
    # RAG messages (if applicable)

    def normalize_message(msg):
        # filter out system messages and tool returns
        if msg["role"] == "system" or msg["role"] == "tool":
            return None
        
        # messages retreived from the DB
        if isinstance(msg, dict):
            return msg
        
        # messages in the form of ChatCompletionMessage objects
        
        # filter out of its an assistant calling a function (contents are none)
        if msg.content is None:
            return None
    
        return {
            "role": msg.role,
            "content": msg.content,
        }
    
    normalized_messages = []
    for m in state.messages:
        norm = normalize_message(m)
        if norm:
            normalized_messages.append(norm)

    non_system = [m for m in normalized_messages]
    
    to_summarize = non_system[:-NUM_RECENT_MESSAGES_TO_KEEP]
    recent = non_system[-NUM_RECENT_MESSAGES_TO_KEEP:]

    # Count characters
    char_count = sum(len(m["content"]) for m in to_summarize)
    if char_count < SUMMARY_TRIGGER_CHAR_COUNT:
        # uprint("Conversation not long enough", OutGoingDataType.LOG)
        return state.messages  # Sliding window of conversation is too short to be summarized

    previous_summary = next((m for m in reversed(normalized_messages) 
        if m["role"] == "system" and "[Summary of previous context]" in m["content"]),
        None
    )

    summarization_prompt = [
        {"role": "system", "content": """You are summarizing a conversation between a user and an assistant. Your goal is to capture key context that will help the assistant continue the conversation intelligently in the future.

        Please extract and clearly summarize:

        1. Any long-term goals the user mentions
        2. Important facts, plans, or information shared by the user
        3. Decisions or conclusions reached
        4. Clarifications, corrections, or preferences the user expresses
        5. Useful assistant knowledge that may apply again later
         
        Keep the summary under 150 words. Use bullet points or short, clear sentences.
        """}
    ]

    # If previous summary exists, inject it as well
    if previous_summary:
        summarization_prompt.append({"role": "assistant", "content": previous_summary["content"]})

    # now add the rest of the messages to summarize
    summarization_prompt.extend(to_summarize)

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=summarization_prompt
    )

    summary = response.choices[0].message.content

    # Replace old messages with a summary
    summary_msg = {"role": "system", "content": f"[Summary of previous context]: {summary}"}

    return [state.messages[0], summary_msg] + recent


def handle_tool_calls(msg, chat_id):
    times = 0

    while msg.tool_calls:
        if times > MAX_FUNCTION_CALL_DEPTH:
            limit_msg = f"Max function call depth reached ({MAX_FUNCTION_CALL_DEPTH}). Returning control back to the user."
            
            state.messages.append({"role": "tool", "tool_call_id": call.id, "content": limit_msg})
            insert_message(chat_id, "tool", limit_msg)

            uprint(limit_msg, OutGoingDataType.TOOL_RETURN)

            state.messages.append({"role": "assistant", "content": "I've reached the maximum allowed number of tool calls. Requesting permission to continue."})
            insert_message(chat_id, "assistant", "I've reached the maximum allowed number of tool calls. Requesting permission to continue.")
            uprint("I've reached the maximum allowed number of tool calls. Requesting permission to continue.")

            return

        for call in msg.tool_calls:
            fn_name = call.function.name
            args = json.loads(call.function.arguments)
            uprint(f"{fn_name}({', '.join(repr(v) for v in args.values())})", OutGoingDataType.TOOL_CALL)

            result = tool_functions.get(fn_name, lambda **_: f"Tool {fn_name} not found.")(**args)
            if not isinstance(result, str):
                result = json.dumps(result, indent=2)

            tool_msg = {"role": "tool", "tool_call_id": call.id, "content": result}
            state.messages.append(tool_msg)
            insert_message(chat_id, "assistant", f"tool-call: {fn_name}({', '.join(repr(v) for v in args.values())}), tool-return: {result}")
            uprint(f"{fn_name}: {result}", OutGoingDataType.TOOL_RETURN)

        # Follow up after tool execution
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=state.messages,
            tools=tool_definitions,
            tool_choice="auto"
        )
        msg = response.choices[0].message
        
        state.messages.append(msg)
        insert_message(chat_id, "assistant", msg.content)
        uprint(msg.content)
        times += 1

def chat():
    while True:
        data = json.loads(input())
        data = data[0]
        type = data['type']
        payload = data['payload']

        if type == "switch-chat":
            # If payload is null, create a new chat and return the new state of chats
            if payload is None:
                state.current_chat_id = create_chat("New Chat")
                state.messages = get_chat_messages(state.current_chat_id)
                system_msg = {"role": "system", "content": system_prompt}
                state.messages.append(system_msg)
                insert_message(state.current_chat_id, "system", system_prompt)

                chats = get_chats()
                for chat in chats:
                    chat["active"] = (chat["id"] == state.current_chat_id)
                
                uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)
                uprint(state.current_chat_id, OutGoingDataType.RETURN_CURRENT_CHAT_ID)
            # Else, switch to an existing chat and return all messages from that chat
            else:
                try:
                    new_id = int(payload)
                    uprint(f"Switching to chat ID {new_id}", OutGoingDataType.LOG)
                    state.current_chat_id = new_id
                    state.messages = get_chat_messages(state.current_chat_id)
                    if not state.messages:
                        system_msg = {"role": "system", "content": system_prompt}
                        state.messages.append(system_msg)
                        insert_message(state.current_chat_id, "system", system_prompt)
                    
                    uprint(state.current_chat_id, OutGoingDataType.RETURN_CURRENT_CHAT_ID)

                    mes = get_chat_messages(state.current_chat_id, 10)
                    uprint(mes, OutGoingDataType.RETURN_CHAT_MESSAGES, meta={"paginated": False})
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
            limit = 10
            before_id = float("inf") 
            isPaginated = False

            # if there is a payload, then it is paginated
            try:
                p = json.loads(payload)
                limit = p["limit"]
                before_id = p["before_id"]
                if before_id != float("inf"):
                    isPaginated = True
            except Exception:
                pass
            
            m = get_chat_messages(state.current_chat_id, limit, before_id)
            uprint(m, OutGoingDataType.RETURN_CHAT_MESSAGES, meta={"paginated": isPaginated})

        # Ensure that we have a user input
        if type != "user-message":
            continue

        state.messages.append({"role": "user", "content": payload})
        insert_message(state.current_chat_id, "user", payload)

        # If needed, check for if we need to summarize here
        state.messages = summarize_messages(client, state.current_chat_id)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=state.messages,
            tools=tool_definitions,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        state.messages.append(msg)
        insert_message(state.current_chat_id, msg.role, msg.content)

        if msg.tool_calls:
            handle_tool_calls(msg, state.current_chat_id)
        else:
            uprint(msg.content)

if __name__ == "__main__":
    load_tools()
    threading.Thread(target=lambda: start_file_watcher(load_tools), daemon=True).start()

    # Check if we actually have a DB lol
    init_db()

    # Initialize the id of our most recently modified chat
    # If there are no chats, this creates a default chat and returns its ID
    state.current_chat_id = get_latest_chat_id()
    # Get the messages from that chat, if there are no messages, we need to append the initial system message 
    state.messages = get_chat_messages(state.current_chat_id)
    if not state.messages:
        system_msg = {"role": "system", "content": system_prompt}
        state.messages.append(system_msg)
        insert_message(state.current_chat_id, "system", system_prompt)
    
    chat()