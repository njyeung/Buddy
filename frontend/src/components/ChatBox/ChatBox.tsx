import { useEffect, useRef, useState } from "react";
import type { IncomingData, OutgoingData, OutgoingDataType } from "../../interface";
import Message from "./Message";
import Input from "./Input";


export default function ChatBox({sendData}: {sendData: (type: OutgoingDataType, data: string | null) => void;}) {

  const [messages, setMessages] = useState<(IncomingData | OutgoingData)[]>([]);
  const [earliestMessageId, setEarliestMessageId] = useState<number | null>(null);
  const hasMoreMessages = useRef(true);

  const scrollToBottom = useRef(true);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (scrollRef.current && scrollRef.current.scrollTop === 0) {

        // Request more messages
        sendData("get-chat-messages", JSON.stringify({
          limit: 10,
          before_id: earliestMessageId
        }));

        scrollToBottom.current = false;
      }
    };

    const el = scrollRef.current;
    if (el) 
      el.addEventListener("scroll", handleScroll);

    return () => {
      if (el) el.removeEventListener("scroll", handleScroll);
    };
  }, [messages.length]);

  useEffect(() => {
    const handleChatBoxData = (e: Event) => {

      const customEvent = e as CustomEvent<IncomingData>;
      const { type } = customEvent.detail;

      if (type === "assistant-message") {
        scrollToBottom.current = true
        
        setMessages((prev) => {
          return [...prev, customEvent.detail]
        });
      }

      if (type === "return-chat-messages") {

        scrollToBottom.current = true

        const payload = customEvent.detail.payload as unknown as { id: number; role: string; content: string }[];

        const isPaginated = customEvent.detail.meta.paginated;

        const tmp:(IncomingData | OutgoingData)[] = []
        let newEarliestId: number | null = null;

        if (payload.length < 10) {
          hasMoreMessages.current = false;
        }
        else {
          hasMoreMessages.current = true;
        }

        payload.forEach((data)=> {
          if(data.role == "user") {
            tmp.push({type: "user-message", payload: data.content})
          }
          else if(data.role == "assistant" && !data.content.match(/tool-call: (.+?), tool-return:/)) {
            tmp.push({type: "assistant-message", payload: data.content})
          }
          else {
            // Random tool stuff that doesn't need to be rendered
            tmp.push({type: "tool-call", payload: data.content})
          }

          if (newEarliestId === null || data.id < newEarliestId) {
            newEarliestId = data.id;
          }
        })

        if (newEarliestId !== null) {
          setEarliestMessageId(newEarliestId);
        }
        
        if(isPaginated) {
          scrollToBottom.current = false
          const el = scrollRef.current;
          const prevScrollHeight = el?.scrollHeight ?? 0;

          setMessages((prev) => {
            const updated = [...tmp, ...prev];

            // Wait for DOM to update, then set the height to what was previously 0
            // This corrects the scroll position after earlier messages are added on top
            setTimeout(() => {
              if (el) {
                const newScrollHeight = el.scrollHeight;
                const diff = newScrollHeight - prevScrollHeight;
                el.scrollTop = diff;
              }
            }, 0);

            return updated;
          });
        }
        else {
          scrollToBottom.current = true
          setMessages(tmp);
        }
      }
    };

    window.addEventListener("IncomingDataEvent", handleChatBoxData);

    return () => {
      window.removeEventListener("IncomingDataEvent", handleChatBoxData);
    };
  }, []);

  useEffect(() => {
    if(scrollToBottom.current == true) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }

    let actualCount = 0
    let toolCount = 0
    messages.forEach((msg)=> {
      if(msg.type == "assistant-message" || msg.type == "user-message") {
        actualCount ++;
      }
      if(msg.type == "tool-call") {
        toolCount ++;
      }
    })

    if (actualCount < 5 && hasMoreMessages.current == true) {
      scrollRef.current?.dispatchEvent(new Event("scroll"));
    }
  }, [messages]);

  const handleOutgoingMessage = (s: string) => {
    setMessages((prev) => [...prev, { type: "user-message", payload: s }]);

    scrollToBottom.current = true
    sendData("user-message", s);
  }

  return (
    <section className="flex flex-col w-full h-full">
      <div
      ref={scrollRef} 
      className="overflow-y-auto h-full px-4">
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