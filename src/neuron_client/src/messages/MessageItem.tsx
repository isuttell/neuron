import React, { memo } from "react";
import { Bot, User, Hammer } from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Skeleton } from "@/components/ui/skeleton";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import AudioPlayer from "./AudioPlayer";
import { Message } from "@/slices/messagesSlice";
interface MessageItemProps {
  message: Message;
}

const getFuzzyTime = (date: Date) => {
  const now = new Date();
  const secondsPast = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (secondsPast < 60) {
    return "Just now";
  }
  if (secondsPast < 3600) {
    return `${Math.floor(secondsPast / 60)}m`;
  }
  if (secondsPast <= 86400) {
    return `${Math.floor(secondsPast / 3600)}h`;
  }
  if (secondsPast <= 2592000) {
    return `${Math.floor(secondsPast / 86400)}d`;
  }
  if (secondsPast <= 31536000) {
    return `${Math.floor(secondsPast / 2592000)}mo`;
  }
  return `${Math.floor(secondsPast / 31536000)}y`;
};

const getStatusMessage = (status: string) => {
  if (status === "thinking") {
    return "Thinking...";
  } else if (status === "tools") {
    return "Looking up more information...";
  } else if (status === "streaming") {
    return "Streaming...";
  } else {
    return "";
  }
};

const MessageItem: React.FC<MessageItemProps> = ({
  message: { id, role, content, created_at, status = undefined },
}) => {
  return (
    <Card
      className={`w-full mb-2 ${
        role === "tool" || role === "system" ? "bg-zinc-900" : ""
      }`}
    >
      <CardContent className="pb-1 px-6 pt-6 text-small text-default-400 flex items-start space-x-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={`w-10 h-10 mr-4 ${
                role === "human" ? "bg-accent" : "bg-primary"
              } rounded-full flex items-center justify-center min-w-[40px]`}
            >
              {role === "human" ? (
                <User className="text-white" size={20} />
              ) : null}
              {role === "ai" || role === "system" ? (
                <Bot className="text-black" size={20} />
              ) : null}
              {role === "tool" ? (
                <Hammer className="text-black" size={20} />
              ) : null}
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">
            {role === "human" ? "You" : "AI"}
          </TooltipContent>
        </Tooltip>

        {(!status || status === "streaming") && content.trim().length > 0 ? (
          <ReactMarkdown
            className="space-y-2 flex-1 whitespace-pre-line"
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

                return (
                  <AudioPlayer
                    preload={status === "streaming" ? "none" : "auto"}
                    src={src.toString()}
                  />
                );
              },
              img({ node, src, className = "", children, ...props }) {
                return (
                  <img
                    className={`${className} m-2 float-left w-full  max-w-[512px] rounded-md`}
                    src={src?.replace("http://localhost:5000/", "/")}
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
                      {typeof children === "string"
                        ? children.trim()
                        : children}
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
                  <code
                    className={`${className} whitespace-pre-line`}
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
            }}
          />
        ) : (
          <div className="space-y-2">
            <Skeleton className="h-4 w-[250px]" />
            <Skeleton className="h-4 w-[200px]" />
            {status && status !== "streaming" && (
              <p className="text-sm text-gray-500">
                {getStatusMessage(status)}
              </p>
            )}
          </div>
        )}
      </CardContent>
      <CardFooter className="gap-3">
        <div className="flex gap-1 flex-1 text-gray-500 space-x-2">
          <div className="flex-1" />
          <p className="text-sm text-gray-700">{id}</p>
          <Tooltip>
            <TooltipTrigger asChild>
              <p className="text-sm hover:text-gray-700">
                {getFuzzyTime(new Date(created_at))}
              </p>
            </TooltipTrigger>
            <TooltipContent side="right">
              {new Date(created_at).toLocaleString()}
            </TooltipContent>
          </Tooltip>
        </div>
      </CardFooter>
    </Card>
  );
};

export default memo(MessageItem);
