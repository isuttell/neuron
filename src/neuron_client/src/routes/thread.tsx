import { useEffect, useRef } from "react";
import { Trash } from "lucide-react";
import { useParams, useNavigate } from "react-router-dom";
import MessageForm from "../messages/MessageForm";
import MessageItem from "../messages/MessageItem";
import { useAppSelector, useAppDispatch } from "../hooks";
import { ScrollArea } from "@/components/ui/scroll-area";

import { shallowEqual } from "react-redux";
import { RootState } from "../store";
import { Button } from "@/components/ui/button";
import EditThreadDialog from "../threads/EditThreadDialog";
import Loading from "@/lib/loading";
import { getActivePersonalityId } from "../slices/personalitiesSlice";

const selectThread = (state: RootState, threadId?: string) =>
  state.threads.threads.find((thread) => thread.id === threadId);

const selectMessages = (state: RootState, threadId?: string) =>
  state.messages.messages.filter((message) => message.thread_id === threadId);

const getStatusMessage = (status: string) => {
  if (status === "thinking") {
    return "Thinking...";
  } else if (status === "tools") {
    return "Working...";
  } else {
    return "";
  }
};

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

  useEffect(() => {
    // Get the thread and its messages any time the id changes
    dispatch({
      type: "socket/GetThread",
      thread_id: threadId,
    });
    dispatch({
      type: "socket/GetThreadMessages",
      thread_id: threadId,
    });
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
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, messagesEndRef.current, thread?.status]);

  if (!thread) {
    return <Loading />;
  }

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">{thread.name}</h1>
        <div className="flex-1" />
        <EditThreadDialog thread={thread} />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            dispatch({ type: "socket/DeleteThread", thread_id: thread.id });
            navigate("/");
          }}
        >
          <Trash className="size-4" />
          <span className="sr-only">Delete</span>
        </Button>
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="flex flex-col flex-nowrap max-w-[1170px] mx-auto">
          {messages
            .sort((a, b) => (a.created_at > b.created_at ? 1 : -1))
            .map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}
          {thread.message_count === 0 && messages.length === 0 ? (
            <div>No messages</div>
          ) : null}
          {thread.status !== "idle" && (
            <div className="text-sm text-gray-500 my-2">
              {getStatusMessage(thread.status)}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      <div className="bottom-0">
        <MessageForm
          className="max-w-[1170px] mx-auto"
          isLoading={thread.status !== "idle"}
          onSubmit={() => {}}
        />
      </div>
    </div>
  );
}
