// Message -> LLM Reply
// Function -> Call a certain function on the frontend
// log -> dev purposes
export type IncomingDataType = "assistant-message" | "assistant-function" | "log" | "tool-call" | "tool-return";

export interface IncomingData  {
  type: IncomingDataType
  payload: string
}

// Message -> User input
// Function -> Call a function on the backend
export type OutgoingDataType = "user-message" | "user-function";

export interface OutgoingData {
  type: OutgoingDataType
  payload: string
}

export interface Window {
  id: number;
  windowType: "chatbox" | "toolbox";
  props: any
}