import { useEffect, useRef, useState } from "react";
import { Trash, Bot } from "lucide-react";
import { useParams, useNavigate } from "react-router-dom";
import MessageForm from "../messages/MessageForm";
import MessageItem from "../messages/MessageItem";
import { useAppSelector, useAppDispatch } from "../hooks";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { shallowEqual } from "react-redux";
import { RootState } from "../store";
import { Button } from "@/components/ui/button";
import EditThreadDialog from "../threads/EditThreadDialog";
import Loading from "@/lib/loading";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import MediaList from "../messages/MediaList";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchThread, deleteThread } from "../actions/threadActions";
import { fetchMessagesByThread } from "../actions/messageActions";

const selectThread = (state: RootState, threadId?: string) =>
  state.threads.threads.find((thread) => thread.id === threadId);

const selectMessages = (state: RootState, threadId?: string) =>
  state.messages.messages.filter((message) => message.thread_id === threadId);

export default function Thread() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const { threadId } = useParams();
  const thread = useAppSelector(
    (state) => selectThread(state, threadId),
    shallowEqual
  );
  const messages = useAppSelector(
    (state) => selectMessages(state, threadId),
    shallowEqual
  );
  const [showTools, setShowTools] = useState(false);

  useEffect(() => {
    if (!threadId) {
      return;
    }
    dispatch(fetchThread(threadId));
    dispatch(fetchMessagesByThread(threadId));
  }, [threadId]);

  useEffect(() => {
    // If no personality is selected, redirect to the personalities page as its required
    if (!activePersonalityId) {
      navigate("/");
    }
  }, [activePersonalityId]);

  useEffect(() => {
    // Scroll to the bottom of the messages when they change
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "instant" });
    }
  }, [
    messages.length,
    messages.length > 0 && messages[messages.length - 1].content,
    messagesEndRef.current,
    thread?.status,
  ]);

  if (!thread || (thread.message_count > 0 && messages.length === 0)) {
    return <Loading />;
  }

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">{thread.name || "Welcome..."}</h1>
        <div className="flex-1" />

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant={showTools ? "default" : "ghost"}
              size="icon"
              onClick={() => {
                setShowTools(!showTools);
              }}
            >
              <Bot className="size-4" />
              <span className="sr-only">Toggle Tools</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {showTools ? "Hide" : "Show"} Tools
          </TooltipContent>
        </Tooltip>
        <EditThreadDialog thread={thread} />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            navigate("/");
            dispatch(deleteThread(thread.id));
          }}
        >
          <Trash className="size-4" />
          <span className="sr-only">Delete</span>
        </Button>
      </div>
      <div className="flex flex-row flex-1">
        <div className="flex flex-col flex-1">
          <div className="flex-1 overflow-y-auto relative">
            <div className="absolute top-0 left-0 right-0 bottom-0 flex flex-1 flex-col flex-nowrap max-h-full mx-auto overflow-y-auto">
              <div className="max-w-[1170px] w-full mx-auto">
                {messages
                  .filter((message) =>
                    !showTools ? message.type !== "tool" : true
                  )
                  .map((message) => (
                    <MessageItem key={message.id} message={message} />
                  ))}
                {thread.message_count === 0 && messages.length === 0 ? (
                  <div className="m-4 text-center text-muted-foreground">
                    No messages
                  </div>
                ) : null}
                {thread.status !== "idle" ? (
                  <div className="m-4 pl-[70px] space-y-2 flex-1">
                    <Skeleton className="h-4 w-[250px]" />
                    <Skeleton className="h-4 w-[200px]" />
                  </div>
                ) : null}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </div>
          <div className="bottom-0">
            <MessageForm
              status={thread.status}
              className="max-w-[1170px] w-full mx-auto"
              onSubmit={() => {}}
            />
          </div>
        </div>
        <MediaList
          key={thread.id}
          className="max-w-[512px] ml-4 w-full flex-shrink-0 border-l"
          threadId={thread.id}
          messages={messages}
        />
      </div>
    </div>
  );
}
