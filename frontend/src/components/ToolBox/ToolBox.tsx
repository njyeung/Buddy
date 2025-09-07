import { useEffect, useRef } from "react";
import type { IncomingData } from "../../interface";
import ToolMessage from "./ToolMessage";
export default function ToolBox({messages}: {messages: IncomingData[]}) {

  const bottomRef = useRef<HTMLDivElement | null>(null);

  // useEffect(() => {
  //   bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  // }, [messages]);

  useEffect(() => {
    const scrollToBottom = () => {
      console.log("SCROLL TO BOTTOM")
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    window.addEventListener("ToolboxScrollReady", scrollToBottom);
    return () => window.removeEventListener("ToolboxScrollReady", scrollToBottom);
  }, []);

  return (
    <section className="flex flex-col w-full h-full">
      <div className="overflow-y-auto h-full px-4">
        <div className="flex flex-col justify-end gap-5 py-4">
          {messages.map((m, i) => (
            <ToolMessage key={i} message={m} />
          ))}
          <div ref={bottomRef} />    
        </div>
      </div>
      
    </section>
  );
}