
import { useRef } from "react";
import type { IncomingData, OutgoingDataType } from "../../interface";

export default function PromptBox({id, prompt, promptReturn} : { id: number, prompt: IncomingData, promptReturn: (id: number, type: OutgoingDataType, payload: any, meta: string) => void }) {
  
  const inputRef = useRef<HTMLInputElement>(null);


  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault(); // prevent page refresh
    if (inputRef.current) {
      promptReturn(id, "return-prompt", inputRef.current?.value, prompt.meta)
    }
  };

  return <div className="w-full h-full flex justify-center items-center flex-col gap-3 p-3 bg-zinc-900 overflow-x-auto">
    <div className="font-black text-secondary">
      {prompt.meta}
    </div>
    <div className="text-primary-100 text-xs font-mono text-center">
      {prompt.payload}
    </div>
  
    <form onSubmit={handleSubmit} className="w-full">
      <input
        ref={inputRef}
        className="font-mono bg-primary-400 text-sm p-1 text-white w-full"
        type="text"
      />
    </form>
    
  </div>
}