import { useEffect, useRef, useState } from "react";
import type { Chat, OutgoingDataType } from "../interface";
import ScrollableChatName from "./ScrollableChatName";

export default function ChatsBar({ chats, sendData } : { chats : Chat[], sendData: (type: OutgoingDataType, data: string | null) => void;}){
  
  const [sidebarWidth, setSidebarWidth] = useState(70);
  
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);
  const sidebarMin = 0;
  const sidebarMax = 200;

  function startResizing(e: React.MouseEvent) {
    e.preventDefault()
    startXRef.current = e.clientX;
    startWidthRef.current = sidebarWidth;

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", stopResizing);
  }
  function handleMouseMove(e: MouseEvent) {
    const dx = startXRef.current - e.clientX ;
    var newWidth = Math.min(Math.max(startWidthRef.current + dx, sidebarMin), sidebarMax);

    const snapTargets = [0, 70];
    const snapRange = 20;

    // Snap if close to any target
    for (const target of snapTargets) {
      if (Math.abs(newWidth - target) <= snapRange) {
        newWidth = target;
        break;
      }
    }

    setSidebarWidth(newWidth);
  }
  function stopResizing() {
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", stopResizing);
  }


  
  return (
    <>
      <div
      className="flex flex-row w-3 cursor-grabbing h-full justify-center group"
      onMouseDown={startResizing}
      >
        <div className="w-0.5 bg-secondary group-hover:bg-primary-100 transition"></div>
      </div>

      <div style={{ width: sidebarWidth }} className="h-full w-full bg-primary-400 overflow-y-auto overflow-x-hidden select-none text-white text-sm">
        <div className="flex w-full p-1">
          <div
          onClick={()=>{
            sendData("switch-chat", null)
          }} 
          className="p-0.5 border-2 border-secondary group hover:bg-primary-200 transition bg-secondary hover:cursor-pointer rounded-lg">
            <button className="text-lg pointer-events-none">💬</button>
          </div>
        </div>
        
        
        <ul>
        {
          chats.map((chat) => (
            <li key={chat.id}>
              <div 
              onClick={()=>{
                sendData("switch-chat", String(chat.id))
              }}
              key={chat.id} className="cursor-pointer w-full border-primary-200 border-t last:border-b">
                <ScrollableChatName active={chat.active} name={chat.name}></ScrollableChatName>
              </div>
            </li>
            
          ))
        }
        </ul>
      </div>
    </>
  );
}