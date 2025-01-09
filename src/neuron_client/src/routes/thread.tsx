import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import MessageForm from "../messages/MessageForm";
import MessageItem from "../messages/MessageItem";
import { useAppSelector, useAppDispatch } from "../hooks";
import { shallowEqual } from "react-redux";
import { RootState } from "../store";
import Loading from "@/lib/loading";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import MediaList, { getMediaItems } from "../messages/MediaList";
import { fetchMessagesByThread } from "../actions/messageActions";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { postMessageByThread } from "../actions/messageActions";
import { debounce } from "@/lib/utils";
import DeleteThreadButton from "@/components/DeleteThreadButton";
import ToggleSystemMessages from "@/components/ToggleSystemMessages";
import MediaPanelWidth, { WidthMode } from "@/components/MediaPanelWidth";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import { Music2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { togglePlayer } from "@/slices/audioSlice";

const selectThread = (state: RootState, threadId?: string) =>
  state.threads.threads.find((thread) => thread.id === threadId);

const selectMessages = (state: RootState, threadId?: string) =>
  state.messages.messages.filter((message) => message.thread_id === threadId);

export default function Thread() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonalityId = useAppSelector(getActivePersonalityId);

  const [activeTab, setActiveTab] = useState<"media">("media");
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

  const [widthMode, setWidthMode] = useState<WidthMode>(
    localStorage.getItem("widthMode") === "wide"
      ? "wide"
      : localStorage.getItem("widthMode") === "narrow"
      ? "narrow"
      : "hidden"
  );

  useEffect(() => {
    if (!threadId) {
      return;
    }
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
    }, 100);
  }, [lastMessageRef.current]);

  const mediaItems = getMediaItems(messages);

  if (!thread || (thread.message_count > 0 && messages.length === 0)) {
    return <Loading />;
  }

  const filteredMessages = messages
    .slice()
    .map((message) => {
      let content = Array.isArray(message.content)
        ? message.content
            .filter((item) => item.type === "text")
            .map((item) => item.text)
            .join("\n")
        : message.content;

      if (!showTools) {
        content = (content || "").replace(/<\|AI\|>.*?<\|AI\|>/g, "").trim();
      }
      return {
        ...message,
        content,
      };
    })
    .filter((message) =>
      [
        message.content && message.content.length > 0,
        !showTools && typeof message.node === "string"
          ? ["agent", "tools"].includes(message.node)
          : true,
      ].every((condition) => condition)
    );

  const lastUserMessage = filteredMessages
    .slice()
    .reverse()
    .find((message) => message.type === "human");

  return (
    <MediaPlayerProvider>
      <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen">
        <div className="flex justify-between mb-2 border-b pb-2">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-lg lg:text-2xl font-bold ">
            {thread.name || "Welcome..."}
          </h1>
          <div className="flex-1" />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => dispatch(togglePlayer())}
            className="size-10"
          >
            <Music2 className="size-4" />
          </Button>
          <ToggleSystemMessages
            showTools={showTools}
            onToggle={() => setShowTools(!showTools)}
          />
          <MediaPanelWidth widthMode={widthMode} onChange={setWidthMode} />
          <DeleteThreadButton threadId={thread.id} />
        </div>
        <div className="flex flex-row flex-1">
          <div className="flex flex-col flex-1">
            <div className="flex-1 overflow-y-auto relative">
              <div className="absolute top-0 left-0 right-0 bottom-0 flex flex-1 flex-col flex-nowrap max-h-full mx-auto overflow-y-auto">
                <div className="max-w-[1170px] w-full mx-auto">
                  {filteredMessages.map((message) => (
                    <div
                      key={message.id}
                      ref={
                        message.id === lastUserMessage?.id
                          ? lastMessageRef
                          : null
                      }
                    >
                      <MessageItem
                        message={message}
                        showTools={showTools}
                        onPromptClick={debounce((prompt) => {
                          if (!activePersonalityId) {
                            return;
                          }
                          dispatch(
                            postMessageByThread({
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
                thread={thread}
                className="max-w-[1170px] w-full mx-auto mt-2"
                onSubmit={() => {}}
              />
            </div>
          </div>
          <Tabs
            defaultValue={activeTab}
            className={cn(
              "ml-4 pl-4  flex-shrink-0 border-l flex-col flex",
              widthMode === "narrow" && "max-w-[512px] w-1/4",
              widthMode === "wide" && "max-w-[1024px] w-1/2",
              widthMode === "hidden" && "hidden"
            )}
            onValueChange={(value) => {
              setActiveTab(value as "media");
            }}
          >
            <TabsList>
              <TabsTrigger value="media">
                Media
                {mediaItems.length > 0 && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({mediaItems.length})
                  </span>
                )}
              </TabsTrigger>
            </TabsList>
            <div className="flex flex-col flex-1 relative overflow-y-auto">
              <TabsContent
                value="media"
                className={cn(
                  "flex flex-col flex-1 absolute top-0 left-0 right-0 bottom-0",
                  activeTab === "media" ? "flex" : "hidden"
                )}
              >
                {widthMode !== "hidden" ? (
                  <MediaList
                    className="flex-col gap-2"
                    threadId={thread.id}
                    mediaItems={mediaItems}
                    thumbnail_size={widthMode === "narrow" ? "t" : "xl"}
                    showControls={true}
                    autoPlay={true}
                  />
                ) : null}
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </MediaPlayerProvider>
  );
}
