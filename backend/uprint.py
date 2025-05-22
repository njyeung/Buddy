import json
from enum import Enum

class MessageType(str, Enum):
    MESSAGE = "assistant-message"
    TOOL_CALL = "tool-call"
    TOOL_RETURN = "tool-return"
    LOG = "log"
    FUNCTION = "assistant-function"

def uprint(msg: str, msg_type=MessageType.MESSAGE):
    if msg_type not in MessageType:
        raise ValueError(f"Invalid msg_type: {msg_type}. Must be one of: {list(MessageType)}")

    payload = {
        "type": msg_type,
        "payload": msg
    }
    
    print(json.dumps(payload), flush=True)