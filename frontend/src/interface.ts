// Message -> LLM Reply
// Function -> Call a certain function on the frontend
// log -> dev purposes
export type IncomingDataType = "assistant-message" | "assistant-function" |
"tool-call" | "tool-return" | "return-all-chats" | "return-current-chat-id" |
"return-chat-messages";

export interface IncomingData  {
  type: IncomingDataType
  payload: string
  meta?: any
}

// Message -> User input
// Function -> Call a function on the backend
export type OutgoingDataType = "user-message" | "get-chat-messages" |
"user-function" | "switch-chat" | "get-all-chats" | "get-current-chat-id";


export interface OutgoingData {
  type: OutgoingDataType
  payload: any
}

export interface Chat {
  active: boolean
  id: number;
  name: string;
  created_at: string;
}

export interface Window {
  id: number;
  windowType: "chatbox" | "toolbox";
  props: any
}