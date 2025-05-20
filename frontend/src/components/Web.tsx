import { useEffect, useRef, useState } from "react";

export default function Web({ url }: { url: string }) {
  const embedAllowed = useRef(false);
  const [displayFallback, setDisplayFallback] = useState(false);
  useEffect(() => {
    const timeout = setTimeout(() => {
      console.log(embedAllowed.current)
      if(embedAllowed.current == false)
        setDisplayFallback(true);
    }, 1000);

    return () => clearTimeout(timeout);
  }, [url]);

  return displayFallback == false ? (
    <iframe
      src={url}
      className="w-full h-full"
      onLoad={() => {
        embedAllowed.current = true
      }}
    />
  ) : (
    <div className="p-4 flex justify-center text-white items-center h-full w-full bg-zinc-900">
      <div className="text-center">
        <p className="mb-2">This site doesn’t allow embedding.</p>
        <a href={url} target="_blank" rel="noopener noreferrer" className="text-primary-100 underline break-words whitespace-pre-wrap hover:text-primary-200">
          Open in a new tab
        </a>
      </div>
    </div>
  );
}