import { useEffect, useRef, useState } from "react";
import type { IncomingData, OutgoingData, OutgoingDataType } from "../../interface";
import Message from "./Message";
import Input from "./Input";


export default function ChatBox({sendData}: {sendData: (type: OutgoingDataType, data: string) => void;}) {

  const [messages, setMessages] = useState<(IncomingData | OutgoingData)[]>([]);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  
  useEffect(() => {
    const handleIncomingData = (e: Event) => {

      const customEvent = e as CustomEvent<IncomingData>;
      const { type } = customEvent.detail;

      if (type === "assistant-message") {
        setMessages((prev) => {
          return [...prev, customEvent.detail]
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
      const newMsg: OutgoingData = {
        type: "user-message",
        payload: s
      }
      
      return [...prev, newMsg]
    })

    sendData("user-message", s);
  }

  return (
    <section className="flex flex-col w-full h-full">
      <div className="overflow-y-auto h-full px-4">
        <div className="flex flex-col gap-5 py-4">
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