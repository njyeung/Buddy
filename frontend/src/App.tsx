import { useState, useEffect, useRef } from 'react';
import type { OutgoingData, OutgoingDataType, IncomingData, Window as WindowInterface } from './interface';

import Window from './components/window' ;

export default function App() {
  useEffect(()=> {
    // @ts-ignore
    window.receiveData = (data: IncomingData) => {

      const decodedPayload = data.payload
      // .replace(/\\n/g, '\n');
      console.log({
        type: data.type,
        payload: decodedPayload
      })

      const event = new CustomEvent("IncomingDataEvent", { detail: {type: data.type, payload: decodedPayload} });
      window.dispatchEvent(event);

      // if (data.type === "function") {
      //   setChatWindows((prev) => [...prev, { id: Date.now() }]);
      // }
    };
  }, [])
  
  const sendData = (type: OutgoingDataType, data: string) => {
    const payload: OutgoingData = {
      type: type,
      payload: data
    };
    
    // @ts-ignore
    window.invoke(payload);

  };

  const [windows, setWindows] = useState<WindowInterface[]>([{ id: 0, windowType: "chatbox", props: {sendData}}]);

  useEffect(() => {
    // const handleKeyDown = (e: KeyboardEvent) => {
    //   if (e.key === "w") {
    //     setWindows((prev) => [...prev, { id: prev[prev.length-1].id + 1, windowType: "chatbox", props: {sendData}}]);
    //   }
    //   if (e.key === "e") {
    //     setWindows((prev) => prev.length > 1 ? prev.slice(0, -1) : prev);
    //   }
    // };

    // window.addEventListener("keydown", handleKeyDown);
    // return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  

  return (
    <div className="w-full h-screen relative">
      <Window items={windows}></Window>
    </div>
  );
}