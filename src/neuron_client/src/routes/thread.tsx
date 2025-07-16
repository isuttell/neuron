import DeleteThreadDialog from "@/components/DeleteThreadDialog";
import MediaPanelToggle from "@/components/MediaPanelToggle";
import MediaTimeline from "@/components/MediaTimeline";
import ThreadHeaderActions from "@/components/ThreadHeaderActions";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Spinner } from "@/components/ui/spinner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  const [isMediaPanelVisible, setIsMediaPanelVisible] = useState(() => {
    // Desktop: sticky behavior (restore from localStorage)
    // Mobile: always start hidden (dialog covers content)
    const isMobileView = window.innerWidth < 1024;
    return isMobileView ? false : localStorage.getItem("mediaPanelVisible") === "true";
  });
  const [isMobile, setIsMobile] = useState(false);

  // Dialog states
  const [isEditPersonalityOpen, setIsEditPersonalityOpen] = useState(false);
  const [isThreadUsersOpen, setIsThreadUsersOpen] = useState(false);
  const [isDeleteThreadOpen, setIsDeleteThreadOpen] = useState(false);

  // Handler for dialog open/close with pointer events fix
  const createDialogHandler = (setter: (open: boolean) => void) => {
    return (open: boolean) => {
      setter(open);
      if (!open) {
        // Clear any stuck pointer-events on body
        setTimeout(() => {
          document.body.style.removeProperty('pointer-events');
        }, 100);
      }
    };
  };

  // Track screen size to determine if we should show dialog or sidebar
  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 1024); // lg breakpoint
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

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
      <div className="flex items-center justify-between mb-2 border-b pb-2 mobile-safe-top">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-lg lg:text-2xl font-bold ">
          {thread.name || "Welcome..."}
        </h1>
        <div className="flex-1" />
        <MediaPanelToggle
          isVisible={isMediaPanelVisible}
          onChange={setIsMediaPanelVisible}
        />
        <ThreadHeaderActions
          threadId={thread.id}
          showTools={showTools}
          onToggleTools={() => setShowTools(!showTools)}
          onEditPersonality={() => setIsEditPersonalityOpen(true)}
          onManageUsers={() => setIsThreadUsersOpen(true)}
          onDeleteThread={() => setIsDeleteThreadOpen(true)}
        />

        {/* Controlled dialogs */}
        {activePersonality && (
          <EditPersonalityDialog
            personality={activePersonality}
            open={isEditPersonalityOpen}
            onOpenChange={createDialogHandler(setIsEditPersonalityOpen)}
            trigger={<></>}
          />
        )}
        {threadId && (
          <ThreadUsersDialog
            threadId={threadId}
            open={isThreadUsersOpen}
            onOpenChange={createDialogHandler(setIsThreadUsersOpen)}
            trigger={<></>}
          />
        )}
        <DeleteThreadDialog
          threadId={thread.id}
          open={isDeleteThreadOpen}
          onOpenChange={createDialogHandler(setIsDeleteThreadOpen)}
          trigger={<></>}
        />
      </div>
      <div className="flex flex-row flex-1">
        <div className="flex flex-col flex-1">
          <div className="flex-1 overflow-y-auto relative">
            <div
              className="h-5 w-full absolute top-0 z-20"
              style={{
                background:
                  "linear-gradient(180deg,rgba(9, 9, 11, 1) 0%, rgba(9,9,11, 0) 100%)",
                backgroundSize: "cover",
              }}
            />
            <div className="absolute top-2 left-0 right-0 bottom-0 flex flex-1 flex-col flex-nowrap max-h-full mx-auto overflow-y-auto">
              <div className="max-w-[1170px] w-full mx-auto relative z-10">
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
                {thread.status !== "idle" && (
                  <div className="flex my-4 pl-5">
                    <Spinner size={48} strokeWidth={2} className="text-muted-foreground" />
                  </div>
                )}
                {thread.message_count === 0 && messages.length === 0 ? (
                  <div className="m-4 text-center text-muted-foreground">
                    No messages
                  </div>
                ) : null}
                <div className="h-screen" />
              </div>
            </div>
            <div
              className="h-16 w-full absolute bottom-0 z-20"
              style={{
                background:
                  "linear-gradient(0deg,rgba(9,9,11, 1) 0%, rgba(9,9,11, 0) 100%)",
                backgroundSize: "cover",
              }}
            />
          </div>
          <div className="bottom-0">
            <ThreadMessageForm thread={thread} className="max-w-[1170px] w-full mx-auto mt-2" />
          </div>
        </div>
        {/* Desktop media panel */}
        <div
          role="complementary"
          className={cn(
            "hidden lg:flex ml-4 pl-4 flex-shrink-0 border-l flex-col w-[512px] max-h-[calc(100vh-5em)]",
            !isMediaPanelVisible && "lg:hidden"
          )}
        >
          {isMediaPanelVisible && threadId ? (
            <MediaTimeline key={threadId} threadId={threadId} />
          ) : null}
        </div>

        {/* Mobile media dialog - only render on mobile */}
        {isMobile && (
          <Dialog
            open={isMediaPanelVisible}
            onOpenChange={setIsMediaPanelVisible}
          >
            <DialogContent className="max-w-[calc(100vw-2rem)] md:max-w-4xl lg:max-w-5xl xl:max-w-6xl w-full h-[90vh] p-0 overflow-hidden grid grid-rows-[auto_1fr] rounded-md">
              <DialogHeader className="p-4 pb-2">
                <DialogTitle className="text-left">Media Timeline</DialogTitle>
              </DialogHeader>
              <div className="overflow-y-auto min-h-0 px-4 pb-4">
                {threadId ? (
                  <MediaTimeline
                    key={threadId}
                    threadId={threadId}
                    layout="grid"
                  />
                ) : null}
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
}
