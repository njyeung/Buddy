import sqlite3
from pathlib import Path
from typing import List, Dict
import json
import state

from uprint import OutGoingDataType, uprint

DB_PATH = Path(__file__).parent / "chat_memory.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_windows (
            chat_id INTEGER PRIMARY KEY,
            window TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
        """)

def create_chat(name: str = None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chats (name) VALUES (?)", (name, ))
        return cursor.lastrowid

def get_chats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM chats ORDER BY last_modified DESC")
        rows = cursor.fetchall()
        return [{"id": row[0], "name": row[1], "created_at": row[2]} for row in rows]

def get_latest_chat_id():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM chats ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
        return create_chat("New Chat")

def insert_message(chat_id: int, role: str, content: str):
    with sqlite3.connect(DB_PATH) as conn:
        if content == None:
            return
        
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)

        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
        cursor.execute("UPDATE chats SET last_modified = CURRENT_TIMESTAMP where id = ?", (chat_id, ))

        chats = get_chats()
        for chat in chats:
            chat["active"] = (chat["id"] == state.current_chat_id)
        uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)

def get_chat_messages(chat_id: int, limit: int = 20, before_id: int = float('inf')) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, role, content FROM messages WHERE chat_id = ? and id < ? ORDER BY id DESC LIMIT ?", (chat_id, before_id, limit))

        results = [{"id": id, "role": role, "content": content} for id, role, content in cursor.fetchall()]
        return results[::-1]
    
def save_chat_window():
    chat_id = state.current_chat_id
    window = state.messages

    def serialize_msg(msg):
        def to_dict(obj):
            if isinstance(obj, dict):
                return {k: to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [to_dict(item) for item in obj]
            elif hasattr(obj, "__dict__"):
                return to_dict(vars(obj))
            else:
                return obj

        if isinstance(msg, dict):
            return to_dict(msg)

        return {
            "role": msg.role,
            "content": msg.content,
            "function_call": to_dict(getattr(msg, "function_call", None)),
            "tool_calls": to_dict(getattr(msg, "tool_calls", None)),
            "refusal": to_dict(getattr(msg, "refusal", None)),
            "annotations": to_dict(getattr(msg, "annotations", [])),
        }

    serializable_window = [serialize_msg(m) for m in window]

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        window_json = json.dumps(serializable_window, ensure_ascii=False)
        cursor.execute("""
            INSERT INTO chat_windows (chat_id, window)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                window = excluded.window,
                updated_at = CURRENT_TIMESTAMP
        """, (chat_id, window_json))


def load_chat_window(chat_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT window FROM chat_windows WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return []