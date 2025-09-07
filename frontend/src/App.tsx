import { useState, useEffect } from 'react';
import type { OutgoingData, OutgoingDataType, IncomingData, Window as WindowInterface, Chat } from './interface';

import Window from './components/Window' ;
import ChatsBar from './ChatsBar/ChatsBar';
import ContextMenu from './ContextMenu';


export default function App() {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().includes("MAC");

      const mod = isMac ? event.metaKey : event.ctrlKey;
      
      const active = document.activeElement;
      
      const isInput =
          active instanceof HTMLInputElement ||
          active instanceof HTMLTextAreaElement ||
          (active instanceof HTMLElement && active.isContentEditable);
      
      if (!isInput) return;
      if (mod) {
        if (event.key === "c") {
          document.execCommand("copy");
          event.preventDefault();
        }

        if (event.key === "v") {
          navigator.clipboard.readText()
          .then((text) => {
            if (document.activeElement instanceof HTMLElement) {
              if (active.isContentEditable) {
                document.execCommand("insertText", false, text); // legacy fallback
              }
            }
          })
        }

        if (event.key === "x") {
          document.execCommand("cut");
          event.preventDefault();
        }
      }
      
    };

    window.addEventListener("keydown", handler);

    return () => {
      window.removeEventListener("keydown", handler);
    };
  }, []);

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
  
  const promptReturn = (id: number, type: OutgoingDataType, payload: any, meta: string) => {
    setWindows(prev => prev.filter(w => w.id !== id));

    sendData(type, payload, meta)
  }
  function handlePrompt(data: IncomingData) {
    if(data.type === "prompt" ) {
      setWindows((prev) => {
        // Open the promptbox window if needed
        const nextId = prev.length > 0 ? prev[prev.length - 1].id + 1 : 1;
        return [...prev, {
          id: nextId,
          windowType: "promptbox",
          props: { id: nextId, prompt: data, promptReturn }
        }];
      });
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
      handlePrompt(data)

      console.log(data)

      const event = new CustomEvent("IncomingDataEvent", { detail: {type: data.type, payload: decodedPayload, meta: data.meta ?? undefined } });
      window.dispatchEvent(event);
    };
  }, [])
  
  const sendData = (type: OutgoingDataType, payload: string | null, meta?: any) => {
    const data: OutgoingData = {
      type: type,
      payload: payload
    };
    
    if(meta) data.meta = meta

    handleToolWindow(data)

    // @ts-ignore
    window.invoke(data);

  };

  const [windows, setWindows] = useState<WindowInterface[]>([{ id: 0, windowType: "chatbox", props: {sendData}}]);
  const [modalOpened, setModalOpened] = useState(false); 
  const [modalContent, setModalContent] = useState<React.ReactNode>(null);

  const openModal = (content: React.ReactNode) => {
    setModalContent(content);
    setModalOpened(true);
  };
  const closeModal = () => {
    setModalContent(null)
    setModalOpened(false);
  }

  return (
    <div className="w-full h-screen flex flex-row relative">
      {
        modalOpened && 
        <ContextMenu setOpened={setModalOpened}>
          { modalContent }
        </ContextMenu>
      }
      <Window items={windows}></Window>
      <ChatsBar chats={chats} sendData={sendData} openModal={openModal} closeModal={closeModal}></ChatsBar>
    </div>
  );
}