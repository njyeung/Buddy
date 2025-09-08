from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import sys
import os
import json
import io
from config import DISTANCE_THRESHOLD, MASTER_MODEL, MAX_FUNCTION_CALL_DEPTH, NUM_RECENT_MESSAGES_TO_KEEP, OS_NAME, NOW, SLAVE_MODEL, SUMMARY_TRIGGER_CHAR_COUNT, TOP_K
import json
from state import tool_definitions, tool_functions
import threading
from watcher import start_file_watcher, load_tools
from uprint import OutGoingDataType, uprint
from storage.chat_storage import delete_chat, init_db, create_chat, insert_message, get_chat_messages, get_latest_chat_id, get_chats, query_embeddings, rename_chat, save_chat_window, load_chat_window
import state



system_prompt = f"""
You are Buddy, an intelligent, resourceful assistant with access to tools and memory. Your goal is to help the user accomplish tasks efficiently and independently, using available tools and your own reasoning.

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

def update_env_file(key: str, value: str, path: str):
    path = Path(path)
    lines = []
    
    if path.exists():
        with path.open("r") as f:
            lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}\n")

    with path.open("w") as f:
        f.writelines(lines)

    load_dotenv()


# This code is so cooked I need to fix this later...
def summarize_messages(client: OpenAI):
    # Strip system prompts and keep last N messages

    # Context layout:
    # Initial system prompt
    # Dynamic summary system prompt (if present)    ]   We are taking care of this section here 
    # Earlier messages (to be summarized)           ]
    # Most recent X messages                        ]
    # RAG messages (if applicable)


    # Filters out tool calls and tool returns
    def normalize_for_summary(msg):
        # If it's a dict (e.g., from DB), access like a dict
        if isinstance(msg, dict):
            if msg["role"] == "system" or msg["role"] == "tool" or msg["content"] == None:
                return None
            return msg

        # If it's a ChatCompletionMessage object (from OpenAI API)
        if hasattr(msg, "role"):
            if msg.role == "system" or msg.role == "tool" or msg.content == None:
                return None
            return {
                "role": msg.role,
                "content": msg.content,
            }

        return None
    
    def normalize_for_recent(msg):
        # If it's a dict (e.g., from DB), access like a dict
        if isinstance(msg, dict):
            if msg["role"] == "system":
                return None
            return msg

        # If it's a ChatCompletionMessage object (from OpenAI API)
        if hasattr(msg, "role"):
            if msg.role == "system":
                return None
            return msg
        return None

    def get_role(msg):
        if isinstance(msg, dict):
            return msg.get("role")
        return getattr(msg, "role", None)
    
    def get_content(msg):
        if isinstance(msg, dict):
            return msg.get("content")
        return getattr(msg, "content", None)
    
    normalized_messages = [norm for m in state.messages if (norm := normalize_for_summary(m))]
    
    to_summarize = normalized_messages[:-NUM_RECENT_MESSAGES_TO_KEEP]

    recent = [
        norm for m in state.messages[-NUM_RECENT_MESSAGES_TO_KEEP:] 
        if (norm := normalize_for_recent(m))
    ]

    # Edge case where the window breaks assistant tool call and tool return
    if recent and get_role(recent[0]) == "tool":
        recent.pop(0)

    # Count characters
    char_count = sum(len(m["content"]) for m in to_summarize)
    if char_count < SUMMARY_TRIGGER_CHAR_COUNT:
        return state.messages  # Sliding window of conversation is too short to be summarized

    previous_summary = next((m for m in reversed(state.messages) 
        if get_role(m) == "system" and "[SUMMARY OF PREVIOUS CONTEXT]" in get_content(m)),
        None
    )

    extra_instruction = (
        "There is a previous summary, marked with [SUMMARY OF PREVIOUS CONTEXT]. Prioritize carrying forward its relevant information, especially anything the user has not contradicted or corrected."
        if previous_summary else ""
    )


    prompt = [
        {"role": "system", "content": f"""You are a summarization assistant. Your task is to distill a conversation between a user and an assistant into a compact summary that preserves key context for future reasoning.

        This summary will be used to:
        - Give the assistant memory of important context from earlier in the conversation
        - Supplement retrieval-augmented generation (RAG) results when available
        - Complement the user's global profile, which contains persistent traits, preferences, and long-term goals across all chats
        
        When summarizing, focus on:
        1. Decisions, plans, or tasks mentioned by the user
        2. Corrections, clarifications, or preferences relevant to the current session
        3. Technical details worth recalling in future steps
         
        {extra_instruction}
        
        Limit the summary to 200 words. Write clearly and concisely, using bullet points or short sentences. You may start and end abruptly. Do not annotate your summary.
        """}
    ]

    # If previous summary exists, inject it as well
    if previous_summary:
        prompt.append({"role": "user", "content": previous_summary["content"]})

    # The section of the conversation to summarize
    conversation_text = ""
    for m in to_summarize:
        role = m["role"].capitalize()
        conversation_text += f"{role}: {m['content'].strip()}\n\n"
    
    # Add onto prompt
    if previous_summary:
        prompt.append({
        "role": "user",
        "content": f"Here are the new messages since the previous summary. Please update and merge with the above summary: \n\n{conversation_text}"
        })
    else:
        prompt.append({
            "role": "user",
            "content": f"Here is the full conversation so far. Please summarize it: \n\n{conversation_text}"
        })
    
    # uprint(f"[CONVERSATION LONG ENOUGH] {char_count}", OutGoingDataType.LOG)
    # uprint(f"[TO SUMMARIZE]: {prompt}" )
    # uprint(f"[PREVIOUS SUMMARY] {previous_summary}", OutGoingDataType.LOG)
    # uprint(f"[CONTENT OF PRVIOUS SUMMARY] {previous_summary}")

    response = client.chat.completions.create(
        model=SLAVE_MODEL,
        messages=prompt
    )

    summary = response.choices[0].message.content

    # Replace old messages with a summary
    summary_msg = {"role": "system", "content": f"[SUMMARY OF PREVIOUS CONTEXT]: {summary}"}

    # uprint(f"[CONTEXT WINDOW]: {[state.messages[0], summary_msg] + recent}" )
    return [state.messages[0], summary_msg] + recent

def handle_tool_calls(msg, chat_id):
    times = 0

    while msg.tool_calls:
        if times > MAX_FUNCTION_CALL_DEPTH:
            limit_msg = f"Max function call depth reached ({MAX_FUNCTION_CALL_DEPTH}). Returning control back to the user."
            
            # Add tool responses for each pending call
            for call in msg.tool_calls:
                tool_response = {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": limit_msg
                }
                state.messages.append(tool_response)
                insert_message(chat_id, "tool", limit_msg)
                uprint(limit_msg, OutGoingDataType.TOOL_RETURN)
                save_chat_window()

            assistant_msg = {
                "role": "assistant",
                "content": "I've reached the maximum allowed number of tool calls. Requesting permission to continue."
            }
            state.messages.append(assistant_msg)
            insert_message(chat_id, "assistant", assistant_msg["content"])
            uprint(assistant_msg["content"])
            save_chat_window()

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
            save_chat_window()

        # Follow up after tool execution
        response = state.client.chat.completions.create(
            model=MASTER_MODEL,
            messages=state.messages,
            tools=tool_definitions,
            tool_choice="auto"
        )
        msg = response.choices[0].message
        
        state.messages.append(msg)
        insert_message(chat_id, "assistant", msg.content)
        uprint(msg.content)
        save_chat_window()

        times += 1

# Returns True if the type is handled, false otherwise
def handle_types(type, payload, meta):
    match type:
        case "switch-chat":
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
                
                # Return new state of chats
                uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)
                uprint(state.current_chat_id, OutGoingDataType.RETURN_CURRENT_CHAT_ID)
                # Empty thread (except for system msg), but forces an update on the frontend
                mes = get_chat_messages(state.current_chat_id, 10)
                uprint(mes, OutGoingDataType.RETURN_CHAT_MESSAGES, meta={"paginated": False})

            # Else, switch to an existing chat and return all messages from that chat
            else:
                try:
                    new_id = int(payload)
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
            
        case "get-all-chats":
            chats = get_chats()
            for chat in chats:
                chat["active"] = (chat["id"] == state.current_chat_id)
            uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)

        case "get-current-chat-id":
            uprint(state.current_chat_id, OutGoingDataType.RETURN_CURRENT_CHAT_ID)

            return True
        case "get-chat-messages":
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

        case "return-prompt":
            if meta == "OPENAI":
                update_env_file("OPENAI", payload, env_path)
                state.client = OpenAI(api_key=os.environ.get("OPENAI"))

            elif meta == "SPOTIFY_CLIENT":
                update_env_file("SPOTIFY_CLIENT_ID", payload, env_path)

            elif meta == "SPOTIFY_CLIENT_SECRET":
                update_env_file("SPOTIFY_CLIENT_SECRET", payload, env_path)
            
            elif meta == "SERPAPI":
                update_env_file("SERPAPI_API_KEY", payload, env_path)
            
        case "rename-chat":
            rename_chat(chat_id=meta, new_name=payload)
            chats = get_chats()
            for chat in chats:
                chat["active"] = (chat["id"] == state.current_chat_id)
            uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)
        
        case "delete-chat":
            delete_chat(payload)

            state.current_chat_id = get_latest_chat_id()

            chats = get_chats()
            for chat in chats:
                chat["active"] = (chat["id"] == state.current_chat_id)
            
            uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)

def chat():
    while True:
        data = json.loads(input())
        data = data[0]
        type = data['type']
        payload = data['payload']
        meta = data.get('meta')

        handle_types(type, payload, meta)

        # Ensure that we have a user input
        if type != "user-message":
            continue

        state.messages.append({"role": "user", "content": payload})
        insert_message(state.current_chat_id, "user", payload)

        # If needed, check for if we need to summarize here
        state.messages = summarize_messages(state.client)
        
        # Get emphereal RAG messages
        rag_results = query_embeddings(state.current_chat_id, payload, TOP_K)
        filtered_rag_results = [r for r in rag_results if r['distance'] < DISTANCE_THRESHOLD]

        uprint(f"[RETREIVED] {filtered_rag_results}", OutGoingDataType.LOG)
        rag_messages = [
            {
                "role": "system",
                "content": f"[RAG retrieved message from {r['role']}]: {r['document']}"
            }
            for r in filtered_rag_results
        ]

        save_chat_window()

        augmented_messages = rag_messages + state.messages

        response = state.client.chat.completions.create(
            model=MASTER_MODEL,
            messages=augmented_messages,
            tools=tool_definitions,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        state.messages.append(msg)
        insert_message(state.current_chat_id, msg.role, msg.content)
        save_chat_window()

        if msg.tool_calls:
            handle_tool_calls(msg, state.current_chat_id)
        else:
            uprint(msg.content)

        # Persist current message thread to DB
        save_chat_window()

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    load_tools()
    threading.Thread(target=lambda: start_file_watcher(load_tools), daemon=True).start()

    # Check if we actually have a DB lol
    init_db()

    # Initialize the id of our most recently modified chat
    # If there are no chats, this creates a default chat and returns its ID
    state.current_chat_id = get_latest_chat_id()
    # Get the messages from that chat, if there are no messages, we need to append the initial system message 
    state.messages = load_chat_window(state.current_chat_id)

    if not state.messages:
        system_msg = {"role": "system", "content": system_prompt}
        state.messages.append(system_msg)
        insert_message(state.current_chat_id, "system", system_prompt)
        save_chat_window()


    # Make sure .env file exists
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        uprint(".env file not found, creating one")
        env_path.touch()

    load_dotenv()

    # API key not found, prompt user for one
    api_key = os.environ.get("OPENAI")
    if not api_key:
        uprint("OPENAI not found in environment. Please paste your OpenAI API key", OutGoingDataType.PROMPT, "OPENAI")
    else:
        state.client = OpenAI(api_key=os.environ.get("OPENAI"))

    chat()