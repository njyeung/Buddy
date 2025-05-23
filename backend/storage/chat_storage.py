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

def get_chat_messages(chat_id: int) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
        return [{"role": role, "content": content} for role, content in cursor.fetchall()]