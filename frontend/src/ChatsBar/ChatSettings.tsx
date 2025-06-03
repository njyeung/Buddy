import { useState } from "react";
import type { Chat, OutgoingDataType } from "../interface";

export default function ChatSettings({chat, sendData, closeModal} : {chat: Chat, sendData: (type: OutgoingDataType, data: string | null, meta?: any) => void , closeModal: () => void}) {

    const [newName, setNewName] = useState("");

  return <div className="w-full h-full flex flex-col justify-between">
    <div className="mb-2">
      <div className="text-white text-lg mb-2">
        Rename <span className="text-primary-100">"{chat.name}"</span> 
      </div>
      <input
      autoFocus={true}
      placeholder={chat.name}
      value={newName}
      onChange={(e) => setNewName(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          const trimmed = newName.trim();
          if (trimmed.length > 0 && trimmed !== chat.name) {
            sendData("rename-chat", trimmed, chat.id);
          }
          setNewName("");
          closeModal();
        }
      }}
      className="bg-primary-400 rounded-md text-white py-1.5 px-2 text-sm w-full leading-0 outline-none focus:ring-1 focus:ring-primary-100"
      type="text" />
    </div>
    
    <button
    onClick={() => {
      sendData("delete-chat", String(chat.id)); closeModal();
    }}
    onKeyDown={(e) => {
      if (e.key === "Enter") {
        sendData("delete-chat", String(chat.id));
        closeModal()
      }
    }}
    className="bg-red-600 rounded-md w-fit px-3 py-4 leading-0 hover:cursor-pointer hover:bg-red-700 active:bg-red-800 active:scale-[97%] transition-all ">
      <span className="text-md text-white font-bold select-none">Delete Chat</span> 
    </button>
  </div>
}