import { useRef, useState } from "react";

export default function Input({ submitMessage }: { submitMessage: (s: string) => void }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget;
    target.style.height = "auto"; // Reset height
    const newHeight = Math.min(target.scrollHeight, 300);
    target.style.height = `${newHeight}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitMessage(input);
      setInput('');

      // snap back down
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  return (
    <div className="w-full h-full text-primary-100 flex items-start gap-2 p-2">
      <span className="text-primary-100 text-sm select-none font-bold">&gt;</span>
      <textarea
        ref={textareaRef}
        rows={1}
        className="w-full resize-none overflow-y-auto focus:outline-none focus:ring-0 bg-transparent text-sm"
        value={input}
        onInput={(e) => {
          setInput(e.currentTarget.value);
          handleInput(e);
        }}
        onKeyDown={handleKeyDown}
      />
    </div>
  );
}
