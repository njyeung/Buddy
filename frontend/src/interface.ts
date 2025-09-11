// assistant-message -> LLM Reply
// return-chat-messages -> fetched from DB, used to fetch after reload or sync state with backend
// prompt -> backend asking for api keys
// tool-call -> llm called a tool
// tool-return -> llm's tool returned something
// return-all-chats -> response to "get-all-chats"
// return-current-chat-id -> response to switch-chat
// return-chat-messages -> response to switch-chat and get-chat-messages
export type IncomingDataType = "assistant-message" | "assistant-function" |
"tool-call" | "tool-return" | "return-all-chats" | "return-current-chat-id" | "prompt" |
"return-chat-messages";

export interface IncomingData  {
  type: IncomingDataType
  payload: string
  meta?: any
}

// empheral -> whole conversation. Backend evaluates and returns the ai output
// user-messages -> User input
// get-chat-messages -> Get the chat messages of a chat, return type is "return-chat-messages" payload == null means we load the latest 10 chats. 
//                      Otherwise, we are getting paginated and the payload looks like -> { before_id: number , limit: number }
// return-prompt -> response to a "prompt", payload is the answer. Meta contains the meta of the "prompt" incoming data so backend can match up.
// switch-chat -> if payload is null, creates a new chat and returns "return-current-chat-id" and "return-chat-messages", if a chat-id is passed in, backend responds with returns "return-chat-messages"
// get-all-chats -> gets all the chats: their names, ids, etc.
// get-current-chat-id -> Gets the current chat id of the backend
// rename-chat -> payload is new name, meta is chat-id to rename, returns "return-all-chats"
// rename-chat -> payload is chat-id to delete, returns "return-all-chats"
export type OutgoingDataType = "empheral" | "user-message" | "get-chat-messages" | "return-prompt" |
"user-function" | "switch-chat" | "get-all-chats" | "get-current-chat-id" | "rename-chat" | "delete-chat";


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
  windowType: "chatbox" | "toolbox" | "promptbox" | "empheralchat";
  props: any
}