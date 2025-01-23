import React, { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";
import "./Content.css";
import "katex/dist/katex.min.css";
import AudioContent from "./AudioContent";
import ImageContent from "./ImageContent";

interface ContentProps {
  className?: string;
  content: string;
  preload?: string;
  onPromptClick?: (prompt: string) => void;
}

const Content: React.FC<ContentProps> = ({
  className,
  content,
  preload = "auto",
  onPromptClick,
}) => {
  return (
    <ReactMarkdown
      className={cn("flex-1 content", className)}
      key={content}
      children={content}
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeRaw, rehypeKatex]}
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
          if (typeof src !== "string") {
            return null;
          }
          return <AudioContent preload={preload} url={src} />;
        },
        img({ src, alt, className = "" }) {
          if (!src) {
            return null;
          }
          return (
            <ImageContent
              className={`${className} my-2 w-full max-w-[512px] rounded-md`}
              url={src?.replace(/\.[^.]+$/, `_o.webp`)}
              alt={alt}
            />
          );
        },
        //@ts-ignore
        prompt({ node, className, children, ...props }) {
          return (
            <span
              onClick={() => onPromptClick?.(children)}
              className={cn(
                onPromptClick &&
                  "cursor-pointer border-b text-accent hover:text-primary transition-colors duration-300 ease-in-out",
                className
              )}
              {...props}
            >
              {children}
            </span>
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
            <>
              {/* {match[1] === "python" ? <div className="">Run Code</div> : null} */}
              <SyntaxHighlighter
                children={String(children).replace(/\n$/, "")}
                // @ts-ignore
                style={oneDark}
                language={match[1]}
                PreTag="div"
                {...props}
              />
            </>
          ) : (
            <code
              className={`${className || ""} whitespace-pre-line`}
              {...props}
            >
              {children}
            </code>
          );
        },
      }}
    />
  );
};

export default memo(Content);
