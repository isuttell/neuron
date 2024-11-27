import React, { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import AudioPlayer from "./AudioPlayer";
import { cn } from "@/lib/utils";
import "./Content.css";

interface ContentProps {
  className?: string;
  content: string;
  preload?: string;
}

const Content: React.FC<ContentProps> = ({
  className,
  content,
  preload = "auto",
}) => {
  return (
    <ReactMarkdown
      className={cn("flex-1 content", className)}
      key={content}
      children={content}
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={{
        audio({ node }) {
          let src = node?.properties?.src;
          if (!src && node?.children) {
            for (const child of node.children) {
              if (child.type === "element" && child.properties?.src) {
                src = child.properties.src;
                break;
              }
            }
          }
          src =
            typeof src === "string"
              ? src.replace(
                  "http://localhost:5000/",
                  "http://192.168.1.211:5000/"
                )
              : undefined;
          if (!src) {
            return null;
          }

          return <AudioPlayer preload={preload} src={src.toString()} />;
        },
        img({ node, className = "", children, ...props }) {
          return (
            <img
              className={`${className} m-2 float-left w-full max-w-[512px] rounded-md`}
              {...props}
            />
          );
        },
        code({ node, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          if (match && match[1] === "thinking") {
            return (
              <div className="italic relative bg-zinc-900 pt-8 font-sans whitespace-pre-line text-gray-400 p-6 rounded-md">
                <div className="absolute bg-accent text-xs px-2 py-1 top-0 left-0 rounded-tl-md rounded-br-md">
                  Thoughts
                </div>
                {typeof children === "string" ? children.trim() : children}
              </div>
            );
          }
          return match ? (
            <SyntaxHighlighter
              children={String(children).replace(/\n$/, "")}
              // @ts-ignore
              style={oneDark}
              language={match[1]}
              PreTag="div"
              {...props}
            />
          ) : (
            <code className={`${className} whitespace-pre-line`} {...props}>
              {children}
            </code>
          );
        },
      }}
    />
  );
};

export default memo(Content);
