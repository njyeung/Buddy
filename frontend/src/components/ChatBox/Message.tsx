import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState, type ComponentPropsWithoutRef } from "react";
import rehypeKatex from "rehype-katex";
import { twMerge } from "tailwind-merge";
import type { IncomingData, OutgoingData } from "../../interface";

export default function Message({ message }: { message: IncomingData | OutgoingData }) {

  const { type, payload } = message

  if(type != "user-message" && type != "assistant-message") {
    return ""
  }

  const [copyState, setCopyState] = useState("⧉ Copy")
  
  return (
    <div className="text-white">
      {type === "user-message" ? (
        <div className="flex justify-end">
          <span className="rounded-2xl px-3 py-2 bg-secondary text-left max-w-[90%] whitespace-pre-wrap break-words">
            {payload}
          </span>
        </div>
      ) : (
        <div className="flex justify-start">
          <div className="w-full break-words">
              <ReactMarkdown
              remarkPlugins={[remarkGfm]}
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
                  <table className="table-auto border-collapse border border-primary-400 my-4 w-full text-sm break-words">
                    {children}
                  </table>
                ),
                thead: ({ children }) => (
                  <thead className="bg-secondary text-primary-100 break-words">{children}</thead>
                ),
                tbody: ({ children }) => (
                  <tbody className="bg-primary-500">{children}</tbody>
                ),
                tr: ({ children }) => <tr className="border-b border-primary-400 break-words">{children}</tr>,
                th: ({ children }) => <th className="text-left px-3 py-2 border border-primary-400 font-bold break-words">{children}</th>,
                td: ({ children }) => (
                  <td className="px-3 py-2 border border-primary-400 break-words">{children}</td>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc ml-7 mb-4 break-words">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal ml-7 mb-4 break-words">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="text-sm my-3 break-words">{children}</li>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-100 underline whitespace-pre-wrap hover:text-primary-200 transition-colors break-words"
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
                  <strong className="font-bold text-primary-100 inline">
                    {children}
                  </strong>
                ),
                code: (props: ComponentPropsWithoutRef<"code">) => {
                  const { className, children, ...rest } = props;
                  const isInline = !String(className).includes("language-");
                    
                  return isInline ? ( // inline notation
                    <code className="bg-secondary text-white px-1 p-0.5 rounded text-sm break-words break-all whitespace-pre-wrap">
                      {children}
                    </code>
                  ) : ( // code block
                    <pre className="mb-4">
                      <div className="bg-secondary flex items-center justify-between font-mono px-2 py-1 text-sm">
                        <h5 className="text-primary-100">{className?.split("language-")}</h5>
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
                      <div className=" bg-zinc-900 overflow-x-auto p-4 rounded text-sm">
                        <code {...rest} className={twMerge(className, "overflow-x-auto")}>
                        {children}
                      </code>
                      </div>
                    </pre>
                  );
                },
              }}
              >
                {payload}
              </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
