import { useState, useEffect, useRef } from 'react';
import type { OutgoingData, OutgoingDataType, IncomingData, Window as WindowInterface, Chat } from './interface';

import Window from './components/Window' ;
import ChatsBar from './ChatsBar/ChatsBar';


export default function App() {


  function handleToolWindow(data: IncomingData | OutgoingData) {
    if (data.type === "tool-call" || data.type === "tool-return") {

      setWindows((prev) => {
        const toolboxExists = prev.some(win => win.windowType === "toolbox");

        // If toolbox window is already opened, just append to the props 
        if (toolboxExists) {
          return prev.map(win => {
            if (win.windowType === "toolbox") {
              const prevMessages = win.props?.messages ?? [];
              return {
                ...win,
                props: {
                  ...win.props,
                  messages: [...prevMessages, data]
                }
              };
            }
            return win;
          });
        }
        // Open the toolbox window if needed 
        else {
          const nextId = prev.length > 0 ? prev[prev.length - 1].id + 1 : 1;
          return [...prev, {
            id: nextId,
            windowType: "toolbox",
            props: { messages: [data] }
          }];
        }
      });
    }
    else if (data.type === "user-message" || data.type === "switch-chat") {
      setWindows((prev) => prev.filter(win => win.windowType !== "toolbox"));
    }
  }

  const [chats, setChats] = useState<Chat[]>([]);
  function handleReturnAllChats(data: IncomingData) {
    if (data.type === "return-all-chats") {
      setChats(data.payload as unknown as Chat[]);
    }
  }

  function handleReturnCurrentChatId(data: IncomingData) {
    if(data.type === "return-current-chat-id") {
      const id = Number(data.payload);
      setChats(prev =>
        prev.map(chat => ({
          ...chat,
          active: chat.id === id
        }))
      );
    }
  }

  useEffect(()=> {
    const getAllChats : OutgoingData = {
      type: 'get-all-chats',
      payload: null
    }

    // @ts-ignore
    window.invoke(getAllChats)
  }, [])

  useEffect(()=> {
    const getChatMessages : OutgoingData = {
      type: "get-chat-messages",
      payload: null
    }

    // @ts-ignore
    window.invoke(getChatMessages)
  }, [])

  useEffect(()=> {
    const getCurrentChatId : OutgoingData = {
      type: 'get-current-chat-id',
      payload: null
    }

    // @ts-ignore
    window.invoke(getCurrentChatId)
  }, [])

  useEffect(()=> {
    // @ts-ignore
    window.receiveData = (data: IncomingData) => {

      const decodedPayload = data.payload

      handleToolWindow(data)
      handleReturnAllChats(data)
      handleReturnCurrentChatId(data)

      console.log(data)

      const event = new CustomEvent("IncomingDataEvent", { detail: {type: data.type, payload: decodedPayload, meta: data.meta ?? undefined } });
      window.dispatchEvent(event);
    };
  }, [])
  
  const sendData = (type: OutgoingDataType, payload: string | null) => {
    const data: OutgoingData = {
      type: type,
      payload: payload
    };
    
    handleToolWindow(data)

    // @ts-ignore
    window.invoke(data);

  };

  const [windows, setWindows] = useState<WindowInterface[]>([{ id: 0, windowType: "chatbox", props: {sendData}}]);

  return (
    <div className="w-full h-screen flex flex-row relative">
      <Window items={windows}></Window>
      <ChatsBar chats={chats} sendData={sendData}></ChatsBar>
    </div>
  );
}