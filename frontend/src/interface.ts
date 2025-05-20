// Message -> LLM Reply
// Function -> Call a certain function on the frontend
// log -> dev purposes
export type IncomingDataType = "message" | "function" | "log" | "tool-call" | "tool-return";

export interface IncomingData  {
  type: IncomingDataType
  payload: string
}

// Message -> User input
// Function -> Call a function on the backend
export type OutgoingDataType = "message" | "function";

export interface OutgoingData {
  type: OutgoingDataType
  payload: string
}

// Wrapper for the two types of data
export interface ChatMessage {
  role: "user" | "assistant";
  data: IncomingData | OutgoingData;
}


export interface Window {
  id: number;
  windowType: "chatbox" | "iframe";
  props: any
}