import { useState, useEffect, useRef } from 'react';
import type { OutgoingData, OutgoingDataType, IncomingData, Window as WindowInterface } from './interface';

import Window from './components/Window' ;

export default function App() {

  function handleToolWindow(data: IncomingData | OutgoingData) {

    if (data.type === "tool-call" || data.type === "tool-return") {

      // Always open the toolbox window if needed
      setWindows((prev) => {
        const toolboxExists = prev.some(win => win.windowType === "toolbox");

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
    else if (data.type === "user-message") {
      setWindows((prev) => prev.filter(win => win.windowType !== "toolbox"));
    }
  }

  useEffect(()=> {
    // @ts-ignore
    window.receiveData = (data: IncomingData) => {

      const decodedPayload = data.payload

      handleToolWindow(data)

      const event = new CustomEvent("IncomingDataEvent", { detail: {type: data.type, payload: decodedPayload} });
      window.dispatchEvent(event);
    };
  }, [])
  
  const sendData = (type: OutgoingDataType, payload: string) => {
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
    <div className="w-full h-screen">
      <Window items={windows}></Window>
    </div>
  );
}