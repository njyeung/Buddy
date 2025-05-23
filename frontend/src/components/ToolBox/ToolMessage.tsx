import { useEffect, useRef, useState } from "react";
import type { IncomingData } from "../../interface";

export default function ToolMessage({ message }: { message: IncomingData }) {

  const { type, payload } = message;

  if(type != "tool-call" && type != "tool-return") {
    return <div>ATTEMPTED TO PASS NON-TOOLMESSAGE DATA INTO TOOLMESSAGE COMPONENT</div>
  }

  const firstTimeExpand = useRef(true);
  const [expanded, setExpanded] = useState(true);
  const [height, setHeight] = useState('0px');

  const contentRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (contentRef.current) {
      setHeight(expanded ? `${contentRef.current.scrollHeight}px` : '0px');
    }
  }, [expanded]);

  useEffect(() => {
  if (firstTimeExpand.current == true && expanded && contentRef.current) {
    firstTimeExpand.current = false;

    setHeight(`${contentRef.current.scrollHeight}px`);

    // Notify parent after animation
    const timeout = setTimeout(() => {
      window.dispatchEvent(new CustomEvent("ToolboxScrollReady"));
    }, 300);

    return () => clearTimeout(timeout);
  }
}, [expanded]);

  return <div className="text-white">
    {
      type === "tool-call" ?
        <div>
          <div className="bg-secondary font-mono px-2 py-1 text-sm flex items-center justify-between">
            <h1 className="text-primary-100 overflow-hidden whitespace-nowrap truncate">
              {type} -&gt; <span className="text-primary-200">{payload.split("(")[0]}</span> 
            </h1>
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-primary-100 text-xs px-2 py-0.5 rounded hover:bg-primary-600 transition"
            >
              {expanded ? "▲ Hide" : "▼ Show"}
            </button>
          </div>
          <div
            ref={contentRef}
            style={{ maxHeight: height }}
            className="transition-all duration-300 ease-in-out overflow-hidden w-full"
          >
            <div className="bg-zinc-900 p-4 rounded text-sm font-mono whitespace-pre-wrap break-all overflow-x-auto">
              <p>&gt; {payload} </p>
            </div>
          </div>
        </div>
      :
      type === "tool-return" ? 
        <div>
          <div className="bg-secondary font-mono px-2 py-1 text-sm flex items-center justify-between">
            <h1 className="text-primary-100 overflow-hidden whitespace-nowrap truncate">
              {type} -&gt; <span className="text-primary-200">{payload.slice(0, payload.indexOf(":"))}</span>
            </h1>
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-primary-100 text-xs px-2 py-0.5 rounded hover:bg-primary-600 transition"
            >
              {expanded ? "▲ Hide" : "▼ Show"}
            </button>
          </div>

          <div
            ref={contentRef}
            style={{ maxHeight: height }}
            className="transition-all duration-300 ease-in-out overflow-hidden"
          >
            <div className="bg-zinc-900 p-4 rounded text-sm font-mono whitespace-pre-wrap break-all overflow-x-auto">
              <p>
                {payload.slice(payload.indexOf(":")+1)}
              </p>
            </div>
          </div>
        </div> 
      : <></>
  }
  </div>
}