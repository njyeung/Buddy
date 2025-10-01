import json
from enum import Enum

class OutGoingDataType(str, Enum):
    # outgoing audio service message
    AUDIO_SERVICE_RESPONSE = "audio-service-response"

def uprint(msg: str, msg_type=OutGoingDataType.AUDIO_SERVICE_RESPONSE, meta=None):
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