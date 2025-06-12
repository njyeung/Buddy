import sqlite3
from pathlib import Path
import threading
from typing import List, Dict
import json

import openai
import state
import chromadb
from chromadb.config import Settings
from uprint import OutGoingDataType, uprint

DB_PATH = Path(__file__).parent / "chat_memory.db"

chroma_client = None
chroma_collection = None

def init_db():
    global chroma_client, chroma_collection

    chroma_client = chromadb.PersistentClient(
        path=str(Path(__file__).parent / "chroma_index"),
        settings=Settings(allow_reset=True)
    )

    chroma_collection = chroma_client.get_or_create_collection(name="buddy_messages")
    
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

def store_embeddings(chat_id: int, role: str, content: str, msg_id: int, tags: list[str] = None):
    global chroma_collection

    if chroma_collection is None:
        raise Exception("Chroma collection not initialized!")
    
    def task(chat_id, role, content, msg_id, tags):
        embedding_response = state.client.embeddings.create(
            model="text-embedding-3-small",
            input=f"Answer: {content}"
        )
        
        embedding = embedding_response.data[0].embedding

        metadata = {
            "chat_id": str(chat_id),
            "role": role,
            "message_id": str(msg_id)
        }

        if tags is not None:
            metadata["tags"] = ",".join(tags)
        
        chroma_collection.add(
            embeddings=[embedding], 
            documents=[content], 
            ids=[str(msg_id)], 
            metadatas=[metadata]
        )
    
    threading.Thread(
        target=task, 
        args=(chat_id, role, content, msg_id, tags)
    ).start()

def query_embeddings(chat_id: int, content: str, topK: int):
    global chroma_collection

    if chroma_collection is None:
        raise Exception("Chroma collection not initialized!")
    
    embedding_response = state.client.embeddings.create(
        model="text-embedding-3-small",
        input=content
    )
    
    query_embedding = embedding_response.data[0].embedding

    results = chroma_collection.query(query_embeddings=[query_embedding], n_results=topK, include=["metadatas", "documents", "distances"])

    filtered_results = []

    for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
        if meta['chat_id'] != str(chat_id):
            filtered_results.append({
                "document": doc,
                "chat_id": meta['chat_id'],
                "message_id": meta['message_id'],
                "role": meta['role'],
                "distance": dist
            })

    return filtered_results

def create_chat(name: str = None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chats (name) VALUES (?)", (name, ))
        return cursor.lastrowid

def delete_chat(chat_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cursor.execute("DELETE FROM chat_windows WHERE chat_id = ?", (chat_id,))
        cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

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

        msg_id = cursor.lastrowid

        cursor.execute("UPDATE chats SET last_modified = CURRENT_TIMESTAMP where id = ?", (chat_id, ))

        chats = get_chats()
        for chat in chats:
            chat["active"] = (chat["id"] == state.current_chat_id)
        uprint(chats, OutGoingDataType.RETURN_ALL_CHATS)


    if content != None and role != "system" and role != "tool" and not content.startswith("tool-call:"):

        # TODO Add a simple filter for whether or not the message should be embedded
        store_embeddings(chat_id, role, content, msg_id)

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
    

def rename_chat(chat_id: int, new_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE chats SET name = ? WHERE id = ?", (new_name, chat_id))