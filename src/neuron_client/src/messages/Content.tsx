import React, { memo, ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { Components } from "react-markdown";
import type { Element } from "hast";
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
import VideoContent from "./VideoContent";
import ImageContent from "./ImageContent";

interface ContentProps {
  className?: string;
  content: string;
  preload?: "" | "none" | "metadata" | "auto";
  onPromptClick?: (prompt: string) => void;
}

interface CustomComponentProps {
  node?: Element;
  children?: React.ReactNode;
  className?: string;
}

type CustomComponents = Components & {
  transcription: (props: { children: string }) => JSX.Element;
  thinking: (props: { children: string }) => JSX.Element;
  prompt: (props: { children: string; className?: string }) => JSX.Element;
};

const Content: React.FC<ContentProps> = ({
  className,
  content,
  preload = "auto",
  onPromptClick,
}): JSX.Element => {
  return (
    <ReactMarkdown
      className={cn("flex-1 content", className)}
      key={content}
      children={content}
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeRaw, rehypeKatex]}
      components={
        {
          transcription({ children }: { children: string }) {
            return <span className="italic">{children}</span>;
          },
          thinking({ children }: { children: string }) {
            return <span className="text-gray-400">{children}</span>;
          },
          audio({
            node,
          }: CustomComponentProps & ComponentPropsWithoutRef<"audio">) {
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
          video({
            node,
          }: CustomComponentProps & ComponentPropsWithoutRef<"video">) {
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
            return <VideoContent autoPlay={true} url={src} loop={true} />;
          },
          img({ src, alt, width, height }: ComponentPropsWithoutRef<"img">) {
            if (!src) {
              return null;
            }
            return (
              <ImageContent
                url={src}
                alt={alt}
                thumbnail_size="xl"
                width={width ? Number(width) : undefined}
                height={height ? Number(height) : undefined}
              />
            );
          },
          prompt({
            className,
            children,
          }: {
            className?: string;
            children: string;
          }) {
            return (
              <span
                onClick={() => onPromptClick?.(String(children))}
                className={cn(
                  onPromptClick &&
                    "cursor-pointer border-b text-accent hover:text-primary transition-colors duration-300 ease-in-out",
                  className
                )}
              >
                {children}
              </span>
            );
          },
          code({
            className,
            children,
            ...props
          }: CustomComponentProps & ComponentPropsWithoutRef<"code">) {
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
                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag="div"
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
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
        } as CustomComponents
      }
    />
  );
};

export default memo(Content);
