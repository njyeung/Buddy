import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../interface";
import { useEffect, useRef, useState, type ComponentPropsWithoutRef } from "react";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

export default function Message({ message }: { message: ChatMessage }) {
  const { role, data } = message;
  
  const [expanded, setExpanded] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState('0px');

  const [copyState, setCopyState] = useState("⧉ Copy")


  useEffect(() => {
    if (contentRef.current) {
      setHeight(expanded ? `${contentRef.current.scrollHeight}px` : '0px');
    }
  }, [expanded]);
  
  return (
    <div className="text-white">
      {role === "user" ? (
        <div className="flex justify-end">
          <span className="rounded-2xl px-3 py-2 bg-secondary text-left max-w-[90%] whitespace-pre-wrap break-words">
            {data.payload}
          </span>
        </div>
      ) : (
        <div className="flex justify-start">
          <div className="w-full">
            {
              data.type === "message" ?
                <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  input: ({ type, checked }) =>
                  type === "checkbox" ? (
                    checked ?
                      <span className="w-4 h-4 mr-1">✔️</span>
                    : 
                      <span className="w-4 h-4 mr-1">❌</span>
                  ) : (
                    <input type={type} />
                  ),
                  table: ({ children }) => (
                    <table className="table-auto border-collapse border border-primary-400 my-4 w-full text-sm">
                      {children}
                    </table>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-secondary text-primary-100">{children}</thead>
                  ),
                  tbody: ({ children }) => (
                    <tbody className="bg-primary-500">{children}</tbody>
                  ),
                  tr: ({ children }) => <tr className="border-b border-primary-400">{children}</tr>,
                  th: ({ children }) => <th className="text-left px-3 py-2 border border-primary-400 font-bold">{children}</th>,
                  td: ({ children }) => (
                    <td className="px-3 py-2 border border-primary-400">{children}</td>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc ml-7 mb-4">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal ml-7 mb-4">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-sm my-3">{children}</li>
                  ),
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-100 underline break-words whitespace-pre-wrap hover:text-primary-200 transition-colors"
                    >
                      {children}
                    </a>
                  ),
                  p: ({ children }) => (
                    <p className="mb-4 last:mb-0">{children}</p> // markdown turns \n\n into empty paragraphs, they need to be at least 1rem tall
                  ),
                  hr: () => (
                    <hr className="my-4 border-1 border-primary-400" />
                  ),
                  h1: ({ children }) => (
                    <h1 className="text-3xl font-bold mb-4 text-primary-100">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-2xl font-bold mb-4 text-primary-100">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-lg font-bold mb-3 text-primary-100">{children}</h3>
                  ),
                  h4: ({ children }) => (
                    <h4 className="text-lg font-bold mb-2 text-primary-100">{children}</h4>
                  ),
                  h5: ({ children }) => (
                    <h5 className="font-bold mb-2 text-primary-100">{children}</h5>
                  ),
                  h6: ({ children }) => (
                    <h6 className="font-semibold mb-2 text-primary-100">{children}</h6>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-bold block text-primary-100">
                      {children}
                    </strong>
                  ),
                  code: (props: ComponentPropsWithoutRef<"code">) => {
                    const { className, children, ...rest } = props;
                    const isInline = !String(className).includes("language-");
                      
                    return isInline ? ( // inline notation
                      <code className="bg-secondary text-white px-1 p-0.5 rounded text-sm">
                        {children}
                      </code>
                    ) : ( // code block
                      <pre className="mb-4">
                        <div className="bg-secondary flex items-center justify-between font-mono px-2 py-1 text-sm">
                          <h1 className="text-primary-100">{className?.split("language-")}</h1>
                          <button
                            onClick={() => {
                              if(copyState === "⧉ Copy") {
                                setCopyState("✔ Copied")
                                navigator.clipboard.writeText(String(children).trim())
                                setTimeout(() => setCopyState("⧉ Copy"), 1500);
                              }
                            }}
                            className="text-primary-100 text-xs px-2 py-0.5 rounded hover:bg-primary-600 transition"
                          >
                            {copyState}
                          </button>
                        </div>
                        <div className="bg-zinc-900 overflow-x-auto p-4 rounded text-sm">
                          <code className={className} {...rest}>
                          {children}
                        </code>
                        </div>
                      </pre>
                    );
                  },
                }}
                >
                  {data.payload}
                </ReactMarkdown>
              :
              data.type === "tool-call" ?
                <div>
                  <div className="bg-secondary font-mono px-2 py-1 text-sm">
                    <h1 className="text-primary-100">
                      {data.type} -&gt; <span className="text-primary-200">{data.payload.split("(")[0]}</span> 
                    </h1>
                  </div>
                  <div className="bg-zinc-900 overflow-x-auto p-4 rounded text-sm">
                    <h1>&gt; {data.payload} </h1>
                  </div>
                </div>
              :
              data.type === "tool-return" ? 
                <div>
                  <div className="bg-secondary font-mono px-2 py-1 text-sm flex items-center justify-between">
                    <h1 className="text-primary-100">
                      {data.type} -&gt; <span className="text-primary-200">{data.payload.slice(0, data.payload.indexOf(":"))}</span>
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
                    <div className="bg-zinc-900 p-4 rounded text-sm whitespace-pre-wrap">
                      <h1>{data.payload.slice(data.payload.indexOf(":")+1)}</h1>
                    </div>
                  </div>
                </div>
              : 
              <></>
            }
          </div>
        </div>
      )}
    </div>
  );
}
