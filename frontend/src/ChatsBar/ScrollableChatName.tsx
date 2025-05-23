import { useRef, useState, useEffect } from "react";
import { twMerge } from "tailwind-merge";

export default function ScrollableChatName({ name, active }: { name: string, active: boolean }) {

  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLParagraphElement>(null);
  const [shouldScroll, setShouldScroll] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    const text = textRef.current;

    function updateScrollState() {
      if (container && text) {
        setShouldScroll(text.scrollWidth > container.clientWidth);
      }
    }

    updateScrollState(); // run on mount

    // Watch for container resizing
    const observer = new ResizeObserver(updateScrollState);
    if (container) observer.observe(container);

    return () => {
      observer.disconnect();
    };
  }, [name]);

  return (
    <div
    ref={containerRef}
    className={twMerge("scroll-container w-full p-2 hover:bg-secondary transition", active && "bg-secondary")}
    onMouseEnter={() => {
      if (shouldScroll && wrapperRef.current) {
        wrapperRef.current.classList.add("scrolling");
      }
    }}
    onMouseLeave={() => {
      if (wrapperRef.current) {
        wrapperRef.current.classList.remove("scrolling");
      }
    }}
    >
      <div ref={wrapperRef} className="scroll-text-wrapper font-mono">
        <span ref={textRef} 
        className="scroll-text" 
        >{name}</span>
        {
          shouldScroll &&
          <span className="scroll-text">{name}</span>
        }
      </div>
    </div>
  );
}
