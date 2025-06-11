import DeleteThreadButton from "@/components/DeleteThreadButton";
import MediaPanelWidth, { WidthMode } from "@/components/MediaPanelWidth";
import MediaTimeline from "@/components/MediaTimeline";
import ToggleSystemMessages from "@/components/ToggleSystemMessages";
import { ThreadStatusMessage } from "@/components/ThreadStatusMessage";
import { SidebarTrigger } from "@/components/ui/sidebar";
import Loading from "@/lib/loading";
import { cn, debounce } from "@/lib/utils";
import EditPersonalityDialog from "@/personalities/EditPersonalityDialog";
import ThreadUsersDialog from "@/threads/ThreadUsersDialog";
import { useEffect, useRef, useState } from "react";
import { shallowEqual } from "react-redux";
import { useParams } from "react-router-dom";
import {
  fetchMessagesByThread,
  postMessageByThread,
} from "../actions/messageActions";
import { useAppDispatch, useAppSelector } from "../hooks";
import ThreadMessageForm from "../messages/ThreadMessageForm";
import MessageItem from "../messages/MessageItem";
import {
  getMessagesLoading,
  selectThreadMessages,
} from "../slices/messagesSlice";
import { getActivePersonality } from "../slices/personalitiesSlice";
import { selectThread } from "../slices/threadsSlice";

export default function Thread() {
  const dispatch = useAppDispatch();
  const activePersonality = useAppSelector(getActivePersonality);
  const lastMessageRef = useRef<HTMLDivElement | null>(null);
  const { threadId } = useParams();
  const thread = useAppSelector(
    (state) => selectThread(state, threadId),
    shallowEqual
  );
  const loading = useAppSelector(getMessagesLoading);
  const messages = useAppSelector(
    (state) => selectThreadMessages(state, threadId),
    shallowEqual
  );
  const [showTools, setShowTools] = useState(false);

  const [widthMode, setWidthMode] = useState<WidthMode>(
    localStorage.getItem("widthMode") === "wide"
      ? "wide"
      : localStorage.getItem("widthMode") === "narrow"
        ? "narrow"
        : "hidden"
  );

  const filteredMessages = messages
    .slice()
    .filter((message) =>
      [
        (message.textContent && message.textContent.length > 0) ||
        (message.thinkingContent && message.thinkingContent.length > 0),
        !showTools && typeof message.node === "string"
          ? ["agent", "tools"].includes(message.node)
          : true,
      ].every((condition) => condition)
    );

  const lastUserMessage = filteredMessages
    .slice()
    .reverse()
    .find((message) => message.type === "human");

  const lastUserMessageIndex = filteredMessages.findIndex(
    (message) => message.id === lastUserMessage?.id
  );

  useEffect(() => {
    if (!threadId) {
      return;
    }
    dispatch(fetchMessagesByThread(threadId));
  }, [threadId, dispatch]);

  useEffect(() => {
    // Only scroll when the last human message changes or system messages are toggled
    setTimeout(() => {
      if (lastMessageRef.current) {
        lastMessageRef.current.scrollIntoView({
          behavior: "instant",
          block: "start",
        });
      }
    }, 0);
  }, [lastUserMessageIndex, filteredMessages.length]);

  if (!thread || (loading && messages.length === 0)) {
    return <Loading />;
  }

  const handlePromptClick = debounce<[string], void>((prompt) => {
    if (!thread) return;
    dispatch(
      postMessageByThread({
        threadId: thread.id,
        prompt,
        personalityId: thread.personality_id,
      })
    );
  }, 100);

  return (
    <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen">
      <div className="flex justify-between mb-2 border-b pb-2">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-lg lg:text-2xl font-bold ">
          {thread.name || "Welcome..."}
        </h1>
        <div className="flex-1" />
        <ToggleSystemMessages
          showTools={showTools}
          onToggle={() => setShowTools(!showTools)}
        />
        <MediaPanelWidth widthMode={widthMode} onChange={setWidthMode} />
        {activePersonality && (
          <EditPersonalityDialog personality={activePersonality} />
        )}
        {threadId && <ThreadUsersDialog threadId={threadId} />}
        <DeleteThreadButton threadId={thread.id} />
      </div>
      <div className="flex flex-row flex-1">
        <div className="flex flex-col flex-1">
          <div className="flex-1 overflow-y-auto relative">
            <div className="absolute top-0 left-0 right-0 bottom-0 flex flex-1 flex-col flex-nowrap max-h-full mx-auto overflow-y-auto">
              <div className="max-w-[1170px] w-full mx-auto">
                {filteredMessages.map((message, index) => (
                  <div
                    key={message.id}
                    ref={index === lastUserMessageIndex ? lastMessageRef : null}
                  >
                    <MessageItem
                      messageId={message.id}
                      showTools={showTools}
                      onPromptClick={handlePromptClick}
                    />
                  </div>
                ))}
                {thread.message_count === 0 && messages.length === 0 ? (
                  <div className="m-4 text-center text-muted-foreground">
                    No messages
                  </div>
                ) : null}
                <div className="h-screen" />
              </div>
            </div>
          </div>
          <div className="bottom-0">
            {thread && (
              <ThreadStatusMessage
                thread={thread}
                className="max-w-[1170px] w-full mx-auto px-4"
              />
            )}
            <ThreadMessageForm
              thread={thread}
              className="max-w-[1170px] w-full mx-auto"
            />
          </div>
        </div>
        <div
          role="complementary"
          className={cn(
            "ml-4 pl-4 flex-shrink-0 border-l flex-col flex max-h-[calc(100vh-5em)]",
            widthMode === "narrow" && "max-w-[512px] w-1/4",
            widthMode === "wide" && "max-w-[1024px] w-1/2",
            widthMode === "hidden" && "hidden"
          )}
        >
          {widthMode !== "hidden" && threadId ? (
            <MediaTimeline key={threadId} threadId={threadId} widthMode={widthMode} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
