import json
from enum import Enum

class OutGoingDataType(str, Enum):
    # Prompts for api keys
    PROMPT = "prompt"
    
    MESSAGE = "assistant-message"
    TOOL_CALL = "tool-call"
    TOOL_RETURN = "tool-return"
    LOG = "log"
    RETURN_ALL_CHATS = "return-all-chats" # payload: id, name, and time-created of all chats
    RETURN_CURRENT_CHAT_ID = "return-current-chat-id" # payload: id of current chat
    
    # Returns from switch-chat
    # switch-chat either returns the id in NEW_CHAT if no id was passed in, or RETURN_CHAT_MESSAGES
    # if a chat id was passed in. 
    NEW_CHAT = "new-chat" # payload: id of new chat
    RETURN_CHAT_MESSAGES = "return-chat-messages" # payload: all messages of the new chat
    
    # Audio service types
    BACKEND_AUDIO_SERVICE = "backend-audio-service" # request from backend to audio service

    EMPHERAL_RESPONSE = "empheral-response" # response to empheral thread
    
def uprint(msg: str, msg_type=OutGoingDataType.MESSAGE, meta=None):
    if msg == None:
        return
    
    if msg_type not in OutGoingDataType:
        raise ValueError(f"Invalid msg_type: {msg_type}. Must be one of: {list(OutGoingDataType)}")

    payload = {
        "type": msg_type,
        "payload": msg
    }
    
    if meta is not None:
        payload["meta"] = meta

    try:
        print(json.dumps(payload), flush=True)
    except:
        print(payload, flush=True)