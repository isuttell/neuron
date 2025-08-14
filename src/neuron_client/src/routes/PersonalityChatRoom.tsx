import PersonalityRoomHeaderActions from "@/components/PersonalityRoomHeaderActions";
import MediaPanelToggle from "@/components/MediaPanelToggle";
import MediaTimeline from "@/components/MediaTimeline";
import { SidebarTrigger } from "@/components/ui/sidebar";
import DeletePersonalityRoomDialog from "@/components/DeletePersonalityRoomDialog";
import { Spinner } from "@/components/ui/spinner";
import Loading from "@/lib/loading";
import PersonalityRoomUsersDialog from "@/rooms/PersonalityRoomUsersDialog";
import { ErrorPage } from "@/components/ErrorPage";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn, debounce } from "@/lib/utils";
import { useEffect, useRef, useState } from "react";
import { shallowEqual } from "react-redux";
import { useParams, useNavigate } from "react-router-dom";
import {
  sendPersonalityMessage,
  updatePersonalityMessage,
  fetchPersonalityMessages,
} from "../actions/personalityChatActions";
import * as personalityRoomActions from "../actions/personalityRoomActions";
import { useAppDispatch, useAppSelector } from "../hooks";
import { usePersonalityRoom } from "../hooks/usePersonalityRoom";
import PersonalityChatForm from "../messages/PersonalityChatForm";
import PersonalityChatItem from "../messages/PersonalityChatItem";
import {
  getPersonalityChatLoading,
  getPersonalityChatMessagesByRoom,
} from "../slices/personalityChatSlice";
import { getPersonality, getPersonalitiesError } from "../slices/personalitiesSlice";
import { getPersonalityRoom, getPersonalityRoomError } from "../slices/personalityRoomSlice";
import { selectMediaByRoomId } from "../slices/mediaSlice";
import { getCurrentUser } from "../slices/appSlice";
import { toast } from "sonner";
import { classifyErrors, hasError } from "../lib/errorClassification";

export default function PersonalityChatRoom() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const currentUser = useAppSelector(getCurrentUser);
  const lastMessageRef = useRef<HTMLDivElement | null>(null);
  const skeletonRef = useRef<HTMLDivElement | null>(null);
  const { personalityId, roomId } = useParams();

  // Get error states for classification and room joining control
  const personalitiesError = useAppSelector(getPersonalitiesError);
  const roomError = useAppSelector(getPersonalityRoomError);
  const hasErrors = hasError(personalitiesError, roomError);

  // Use the specialized personality room hook with roomId
  const { isSubscribed } = usePersonalityRoom(personalityId, roomId, hasErrors);

  const personality = useAppSelector(
    (state) => personalityId ? getPersonality(state, personalityId) : undefined,
    shallowEqual
  );

  const room = useAppSelector(
    (state) => roomId ? getPersonalityRoom(state, roomId) : undefined,
    shallowEqual
  );

  const loading = useAppSelector(getPersonalityChatLoading);

  const messages = useAppSelector(
    (state) => getPersonalityChatMessagesByRoom(state, personalityId, roomId),
    shallowEqual
  );

  const roomMedia = useAppSelector(
    (state) => roomId ? selectMediaByRoomId(state, roomId) : [],
    shallowEqual
  );

  // Check if we have a streaming message
  // const hasStreamingMessage = messages.some(msg => 'isStreaming' in msg && msg.isStreaming);

  // Check if AI is working (status is not empty and not idle)
  const isAiWorking = room?.status !== "" && room?.status !== null && room?.status !== "contemplating";

  // Edit state management
  const [editingMessage, setEditingMessage] = useState<{ id: string; content: string } | null>(null);

  // Media panel state
  const [isMediaPanelVisible, setIsMediaPanelVisible] = useState(() => {
    // Desktop: sticky behavior (restore from localStorage)
    // Mobile: always start hidden (dialog covers content)
    const isMobileView = window.innerWidth < 1024;
    return isMobileView ? false : localStorage.getItem("mediaPanelVisible") === "true";
  });
  const [isMobile, setIsMobile] = useState(false);

  // Dialog states
  const [isRoomUsersOpen, setIsRoomUsersOpen] = useState(false);
  const [isDeleteRoomOpen, setIsDeleteRoomOpen] = useState(false);

  // Classify errors for UI handling - roomError takes priority as it's more specific
  const errorType = classifyErrors(roomError, personalitiesError);

  // Show toast for network errors
  useEffect(() => {
    if (errorType === 'network_error') {
      toast.error('Network connection failed. Please check your internet connection.', {
        duration: 5000,
      });
    }
  }, [errorType]);

  // Fetch room details and messages when IDs are available
  useEffect(() => {
    if (personalityId && roomId) {
      // Let Redux handle all errors through slice reducers
      dispatch(personalityRoomActions.getPersonalityRoom({ personalityId, roomId }));
      dispatch(fetchPersonalityMessages({ personalityId, roomId }));
    }
  }, [dispatch, personalityId, roomId]);

  // Auto-scroll to latest message or skeleton bars
  useEffect(() => {
    setTimeout(() => {
      if (isAiWorking && skeletonRef.current) {
        skeletonRef.current.scrollIntoView({
          behavior: "instant",
          block: "end",
        });
      } else if (lastMessageRef.current) {
        lastMessageRef.current.scrollIntoView({
          behavior: "instant",
          block: "end",
        });
      }
    }, 100);
  }, [messages.length, isAiWorking]);

  // Track screen size to determine if we should show dialog or sidebar
  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 1024); // lg breakpoint
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  // Handle errors first
  if (errorType) {
    // Show loading for network errors (toast shown via useEffect above)
    if (errorType === 'network_error') {
      return <Loading />;
    }

    // Show error component for server/auth/not_found errors
    const getErrorMessage = () => {
      if (personalitiesError) return personalitiesError;
      if (roomError?.message) return roomError.message;

      // Fallback messages based on error type
      switch (errorType) {
        case 'not_found':
          return 'This room may have been deleted or you may not have permission to access it.';
        case 'auth_error':
          return 'There was a problem with your authentication. Please log in again.';
        case 'client_error':
          return 'There was a problem with your request. The room may not be accessible.';
        default:
          return 'The server is currently unavailable. Please try again later.';
      }
    };

    return (
      <ErrorPage
        errorType={errorType}
        message={getErrorMessage()}
        onBack={() => navigate('/personalities')}
      />
    );
  }

  // Show loading for normal loading states
  if (!personality || !room || (loading && messages.length === 0)) {
    return <Loading />;
  }

  const handleSendMessage = debounce<[string, File | Blob | undefined], void>((content, file) => {
    if (!personalityId || !roomId || !currentUser?.sub) return;

    if (editingMessage) {
      // Update existing message (files not supported in edit mode)
      dispatch(
        updatePersonalityMessage({
          personalityId,
          messageId: editingMessage.id,
          content,
        })
      );
      setEditingMessage(null); // Clear edit mode
    } else {
      // Send new message
      dispatch(
        sendPersonalityMessage({
          personalityId,
          roomId,
          content,
          userId: currentUser.sub,
          file,
        })
      );
    }
  }, 100);

  const handleEditMessage = (message: { id: string; content: string }) => {
    setEditingMessage(message);
  };

  const handleCancelEdit = () => {
    setEditingMessage(null);
  };

  const handleDeleteRoom = () => {
    setIsDeleteRoomOpen(true);
  };

  const handleManageUsers = () => {
    setIsRoomUsersOpen(true);
  };

  const handlePromptClick = (prompt: string) => {
    if (!personalityId || !roomId || !currentUser?.sub) return;

    // Send the prompt as a new message
    dispatch(
      sendPersonalityMessage({
        personalityId,
        roomId,
        content: prompt,
        userId: currentUser.sub,
      })
    );
  };

  return (
    <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen">
      <div className="flex items-center justify-between mb-2 border-b pb-2 mobile-safe-top">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-lg lg:text-2xl font-bold">
          {room.name}
          {personality && (
            <span className="text-sm text-muted-foreground font-normal ml-2">
              {personality.name}
            </span>
          )}
        </h1>
        <div className="flex-1" />
        <MediaPanelToggle
          isVisible={isMediaPanelVisible}
          onChange={setIsMediaPanelVisible}
        />
        <PersonalityRoomHeaderActions
          personalityId={personality.id}
          roomId={room.id}
          onManageUsers={handleManageUsers}
          onDeleteRoom={handleDeleteRoom}
        />
      </div>

        {/* Controlled dialogs */}
        {personalityId && roomId && (
          <PersonalityRoomUsersDialog
            personalityId={personalityId}
            roomId={roomId}
            open={isRoomUsersOpen}
            onOpenChange={setIsRoomUsersOpen}
            trigger={<></>}
          />
        )}

        <DeletePersonalityRoomDialog
          personalityId={personalityId || ""}
          roomId={roomId || ""}
          roomName={room?.name}
          open={isDeleteRoomOpen}
          onOpenChange={setIsDeleteRoomOpen}
          trigger={<></>}
        />

      <div className="flex flex-row flex-1">
        <div className="flex flex-col flex-1">
          <div className="flex-1 overflow-y-auto relative">
            <div className="absolute top-0 left-0 right-0 bottom-0 flex flex-1 flex-col flex-nowrap max-h-full mx-auto overflow-y-auto">
              <div className="max-w-3xl w-full mx-auto relative z-10 flex flex-grow flex-col">
                <div className="flex-grow" />
                {messages.map((message, index) => (
                  <div
                    key={message.id}
                    ref={index === messages.length - 1 ? lastMessageRef : null}
                  >
                    <PersonalityChatItem
                      message={message}
                      personality={personality}
                      roomId={roomId}
                      onEditMessage={handleEditMessage}
                      onPromptClick={handlePromptClick}
                      promptColor="text-lime-300"
                      promptHoverColor="hover:text-lime-100"
                    />
                  </div>
                ))}

                {loading && (
                  <div className="flex my-4 pl-5">
                    <Spinner size={48} strokeWidth={2} className="text-muted-foreground" />
                  </div>
                )}

                {messages.length === 0 && !loading && (
                  <div className="m-4 text-center text-muted-foreground">
                    Be the first to say hi!
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bottom-0">
            <PersonalityChatForm
              personality={personality}
              room={room}
              onSendMessage={handleSendMessage}
              editingMessage={editingMessage}
              onCancelEdit={handleCancelEdit}
              isSubscribed={isSubscribed}
              className="max-w-3xl w-full mx-auto mt-2"
            />
          </div>
        </div>

        {/* Desktop media panel */}
        <div
          role="complementary"
          className={cn(
            "hidden lg:flex ml-4 pl-4 flex-shrink-0 border-l flex-col max-w-[512px] w-1/3 max-h-[calc(100vh-5em)]",
            !isMediaPanelVisible && "lg:hidden"
          )}
        >
          {isMediaPanelVisible && roomId ? (
            <MediaTimeline key={roomId} mediaItems={roomMedia} contextId={roomId} />
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
                {roomId ? (
                  <MediaTimeline
                    key={roomId}
                    mediaItems={roomMedia}
                    contextId={roomId}
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
