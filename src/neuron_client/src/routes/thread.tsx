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
import MediaList, { getMediaItems } from "../messages/MediaList";
import { fetchThread, deleteThread } from "../actions/threadActions";
import { fetchMessagesByThread } from "../actions/messageActions";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ArtifactViewer, {
  extractAndReplaceArtifacts,
} from "../artifacts/ArtifactViewer";
import { cn } from "@/lib/utils";
import { sendMessage } from "../actions/messageActions";
import TokenCounter from "../messages/TokenCounter";
import { debounce } from "@/lib/utils";

const selectThread = (state: RootState, threadId?: string) =>
  state.threads.threads.find((thread) => thread.id === threadId);

const selectMessages = (state: RootState, threadId?: string) =>
  state.messages.messages.filter((message) => message.thread_id === threadId);

export default function Thread() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonalityId = useAppSelector(getActivePersonalityId);

  const [activeTab, setActiveTab] = useState("media");
  const lastMessageRef = useRef<HTMLDivElement | null>(null);
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
      navigate("/personalities");
    }
  }, [activePersonalityId]);

  useEffect(() => {
    // Scroll to the bottom of the messages when they change
    setTimeout(() => {
      if (lastMessageRef.current) {
        lastMessageRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, 0);
  }, [lastMessageRef.current]);

  const { updatedMessages, artifacts } = extractAndReplaceArtifacts(messages);

  const mediaItems = getMediaItems(messages);

  if (!thread || (thread.message_count > 0 && messages.length === 0)) {
    return <Loading />;
  }
  const { input_tokens, output_tokens, total_tokens } = messages.reduce(
    (results, message) => {
      return {
        input_tokens:
          results.input_tokens + (message.usage_metadata?.input_tokens || 0),
        output_tokens:
          results.output_tokens + (message.usage_metadata?.output_tokens || 0),
        total_tokens:
          results.total_tokens + (message.usage_metadata?.total_tokens || 0),
      };
    },
    { input_tokens: 0, output_tokens: 0, total_tokens: 0 }
  );

  const filteredMessages = updatedMessages.filter((message) =>
    [
      !showTools ? message.type !== "tool" : true,
      !showTools
        ? (typeof message.content === "string" &&
            message.content.indexOf("<|AI|>") !== 0) ||
          typeof message.content !== "string"
        : true,
      message.content && message.content.length > 0,
    ].every((condition) => condition)
  );

  const lastUserMessage =
    filteredMessages.length -
    1 -
    [...filteredMessages]
      .reverse()
      .findIndex((message) => message.type === "human");

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">{thread.name || "Welcome..."}</h1>
        <div className="flex-1" />
        {input_tokens > 0 && output_tokens > 0 && total_tokens > 0 && (
          <TokenCounter
            input_tokens={input_tokens}
            output_tokens={output_tokens}
            total_tokens={total_tokens}
          />
        )}
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
          onClick={debounce(() => {
            navigate("/");
            dispatch(deleteThread(thread.id));
          }, 100)}
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
                {filteredMessages.map((message, index, array) => (
                  <div
                    key={message.id}
                    ref={
                      index === lastUserMessage + 1 ||
                      (index === array.length - 1 && index === lastUserMessage)
                        ? lastMessageRef
                        : null
                    }
                  >
                    <MessageItem
                      message={message}
                      onPromptClick={debounce((prompt) => {
                        if (!activePersonalityId) {
                          return;
                        }
                        dispatch(
                          sendMessage({
                            threadId: thread.id,
                            prompt,
                            personalityId: activePersonalityId,
                          })
                        );
                      }, 100)}
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
            <MessageForm
              status={thread.status}
              className="max-w-[1170px] w-full mx-auto mt-2"
              onSubmit={() => {}}
            />
          </div>
        </div>
        <Tabs
          defaultValue={activeTab}
          className={cn(
            "ml-4 pl-4  flex-shrink-0 border-l flex-col flex",
            activeTab === "media" ? "max-w-[512px] w-1/4" : "w-1/2"
          )}
          onValueChange={(value) => {
            setActiveTab(value);
          }}
        >
          <TabsList>
            <TabsTrigger value="media">Media</TabsTrigger>
            <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
          </TabsList>
          <div className="flex flex-col flex-1 relative overflow-y-auto">
            <TabsContent
              value="media"
              className={cn(
                "flex flex-col flex-1 absolute top-0 left-0 right-0 bottom-0",
                activeTab === "media" ? "block" : "hidden"
              )}
            >
              <MediaList threadId={thread.id} mediaItems={mediaItems} />
            </TabsContent>
            <TabsContent
              value="artifacts"
              className={cn(
                "flex flex-col flex-1 absolute top-0 left-0 right-0 bottom-0",
                activeTab === "artifacts" ? "block" : "hidden"
              )}
            >
              {Object.keys(artifacts).map((key) => (
                <ArtifactViewer key={key} artifacts={artifacts[key]} />
              ))}
              {Object.keys(artifacts).length === 0 && (
                <div className="m-4 text-center text-muted-foreground">
                  No artifacts
                </div>
              )}
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
