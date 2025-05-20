import json
import os
import time
import dateparser
from datetime import datetime
from pathlib import Path
from config import BASE_PATH
import hashlib
from threading import Lock

from tool_decorator import tool

calendar_lock = Lock()

CALENDAR_FILE = BASE_PATH / "storage" / "calendar.json"

def load_calendar():
    with calendar_lock:
        if CALENDAR_FILE.exists():
            with open(CALENDAR_FILE, "r") as f:
                return json.load(f)
    return []

def generate_event_id(event: str, dt: datetime):
    hash_input = f"{event}-{dt.isoformat()}-{time.time()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:8]

def save_calendar(entries):
    with calendar_lock:
        with open(CALENDAR_FILE, "w") as f:
            json.dump(entries, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

def clean_calendar(entries):
    now = datetime.now()
    return [entry for entry in entries if dateparser.parse(entry["datetime"]) > now]

def add_to_calendar(event, datetime_str):
    parsed_time = dateparser.parse(datetime_str)
    if not parsed_time:
        return f"Could not parse datetime: '{datetime_str}'"

    entries = load_calendar()
    entries = clean_calendar(entries)

    entry_id = generate_event_id(event, parsed_time)

    entries.append({
        "id": entry_id,
        "event": event,
        "datetime": parsed_time.isoformat()
    })

    entries.sort(key=lambda e: e["datetime"])
    save_calendar(entries)

    return f"Added event: '{event}' at {parsed_time.strftime('%Y-%m-%d %H:%M')} with ID {entry_id}"

def delete_from_calendar(id):
    entries = clean_calendar(load_calendar())
    new_entries = [e for e in entries if e["id"] != id]

    if len(new_entries) == len(entries):
        return f"No event found with ID '{id}'."

    save_calendar(new_entries)
    return f"Deleted event with ID '{id}'."

def read_calendar():
    entries = clean_calendar(load_calendar())
    save_calendar(entries)
    if not entries:
        return "No upcoming events."

    return "\n".join(
        f"[{entry['id']}] {dateparser.parse(entry['datetime']).strftime('%Y-%m-%d %H:%M')}: {entry['event']}"
        for entry in entries
    )

# Tool Definitions
@tool("Adds a calendar event at a specified date/time (can be natural language like 'tomorrow at 5pm')")
def add_event(event:str, datetime_str:str):
    return add_to_calendar(event, datetime_str)

@tool("Returns a list of upcoming calendar events")
def get_upcoming_events():
    return read_calendar()

@tool("Deletes a calendar event by its id (shown as hash during get_upcoming_events)")
def delete_event(id:str):
    return delete_from_calendar(id)