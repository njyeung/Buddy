import { useEffect, useRef, useState } from "react";
import type { ChatMessage, IncomingData, OutgoingDataType } from "../interface";
import Message from "./Message";
import Input from "./Input";


export default function ChatBox({sendData}: {sendData: (type: OutgoingDataType, data: string) => void;}) {

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  
  useEffect(() => {
    const handleIncomingData = (e: Event) => {

      const customEvent = e as CustomEvent<IncomingData>;
      const { type } = customEvent.detail;

      if (type === "message" || type === "tool-call" || type === "tool-return") {
        setMessages((prev) => {
          const newMsg: ChatMessage = {
            role: "assistant",
            data: customEvent.detail
          }
          return [...prev, newMsg]
        });
      }
    };

    window.addEventListener("IncomingDataEvent", handleIncomingData);

    return () => {
      window.removeEventListener("IncomingDataEvent", handleIncomingData);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleOutgoingMessage = (s: string) => {
    setMessages((prev)=>{
      const newMsg: ChatMessage = {
        role: "user",
        data: {
          type: "message",
          payload: s
        }
      }
      return [...prev, newMsg]
    })

    sendData("message", s);
  }

  return (
  <section className="flex flex-col h-full">
    <div className="flex-1 overflow-y-auto px-4">
      <div className="flex flex-col justify-end min-h-full gap-5 py-4">
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        
      </div>
      <div ref={bottomRef} />
    </div>
    {/* Input bar */}
    <div className="w-full border-t-1 border-t-primary-100 bg-primary-500">
      <Input submitMessage={handleOutgoingMessage}/>
    </div>
  </section>
);
}
