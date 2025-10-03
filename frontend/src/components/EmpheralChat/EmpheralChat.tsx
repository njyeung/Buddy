import { useState, useRef, useEffect } from "react";
import type { OutgoingDataType, IncomingData, OutgoingData } from "../../interface";
import Message from "../ChatBox/Message";
import Input from "../ChatBox/Input";
import EmpheralInput from "./EmpheralInput";
import EmpheralMessage from "./EmpheralMessage";

interface EmpheralMessage {
  type: "user-message" | "assistant-message";
  payload: string;
}

export default function EmpheralChat({sendData}: {sendData: (type: OutgoingDataType, data: string | null) => void;}) {
  const [messages, setMessages] = useState<EmpheralMessage[]>([]);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Listen for assistant responses
  useEffect(() => {
    const handleEmpheralResponse = (e: Event) => {
      const customEvent = e as CustomEvent<IncomingData>;
      const { type, payload } = customEvent.detail;

      if (type === "empheral-response" && isWaitingForResponse) {
        sendData("frontend-audio-service", payload)

        setMessages((prev) => [
          ...prev,
          { type: "assistant-message", payload }
        ]);
        setIsWaitingForResponse(false);
      }
    };

    window.addEventListener("IncomingDataEvent", handleEmpheralResponse);
    return () => window.removeEventListener("IncomingDataEvent", handleEmpheralResponse);
  }, [isWaitingForResponse]);

  const submitMessage = (userInput: string) => {
    if (!userInput.trim() || isWaitingForResponse) return;

    // Add user message to local state
    const newUserMessage: EmpheralMessage = { type: "user-message", payload: userInput };
    const updatedMessages = [...messages, newUserMessage];
    setMessages(updatedMessages);
    setIsWaitingForResponse(true);

    // Send entire conversation to backend using 'empheral' type
    sendData("empheral", JSON.stringify(updatedMessages));
  };

  const clearChat = () => {
    setMessages([]);
    setIsWaitingForResponse(false);
  };

  return (
    <div className="w-full h-full flex flex-col bg-gradient-to-bl from-[#e2c3dc] to-[#d34898] relative">
      {/* Header */}
      <div className="flex justify-between items-center p-3 border-b border-secondary">
        <h2 className="text-[#343131] font-bold">ACA Chat</h2>
        <button
          onClick={clearChat}
          className="text-xs hover:cursor-pointer text-[#343131] hover:text-white transition px-2 py-1 rounded hover:bg-[#302540]"
        >
          Clear
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-[#343131] mt-8">
            <p className="text-lg mb-2">Ephemeral Chat</p>
            <p className="text-sm">Start a temporary conversation. Messages expire after an hour.</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <EmpheralMessage key={index} message={message as IncomingData | OutgoingData} />
          ))
        )}
        
        {isWaitingForResponse && (
          <div className="flex justify-start">
            <div className="text-white italic">Aca ne is thinking...</div>
          </div>
        )}
        
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-secondary">
        <EmpheralInput submitMessage={submitMessage} />
      </div>
    </div>
  );
}