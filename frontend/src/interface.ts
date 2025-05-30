// Message -> LLM Reply
// Function -> Call a certain function on the frontend
// log -> dev purposes
// return-chat-messages -> fetched from DB, used to fetch after reload or sync state with backend
// prompt -> backend asking for api keys
export type IncomingDataType = "assistant-message" | "assistant-function" |
"tool-call" | "tool-return" | "return-all-chats" | "return-current-chat-id" | "prompt" |
"return-chat-messages";

export interface IncomingData  {
  type: IncomingDataType
  payload: string
  meta?: any
}

// Message -> User input
// Function -> Call a function on the backend
export type OutgoingDataType = "user-message" | "get-chat-messages" | "return-prompt" |
"user-function" | "switch-chat" | "get-all-chats" | "get-current-chat-id";


export interface OutgoingData {
  type: OutgoingDataType
  payload: any
  meta?: any
}

export interface Chat {
  active: boolean
  id: number;
  name: string;
  created_at: string;
}

export interface Window {
  id: number;
  windowType: "chatbox" | "toolbox" | "promptbox";
  props: any
}