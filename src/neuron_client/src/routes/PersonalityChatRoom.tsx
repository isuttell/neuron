import PersonalityRoomHeaderActions from "@/components/PersonalityRoomHeaderActions";
import { SidebarTrigger } from "@/components/ui/sidebar";
import DeletePersonalityRoomDialog from "@/components/DeletePersonalityRoomDialog";
import { Spinner } from "@/components/ui/spinner";
import Loading from "@/lib/loading";
import PersonalityRoomUsersDialog from "@/rooms/PersonalityRoomUsersDialog";
import { debounce } from "@/lib/utils";
import { useEffect, useRef, useState } from "react";
import { shallowEqual } from "react-redux";
import { useParams } from "react-router-dom";
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
import { getPersonality } from "../slices/personalitiesSlice";
import { getPersonalityRoom } from "../slices/personalityRoomSlice";
import { getCurrentUser } from "../slices/appSlice";

export default function PersonalityChatRoom() {
  const dispatch = useAppDispatch();
  const currentUser = useAppSelector(getCurrentUser);
  const lastMessageRef = useRef<HTMLDivElement | null>(null);
  const { personalityId, roomId } = useParams();

  // Use the specialized personality room hook with roomId
  const { isSubscribed } = usePersonalityRoom(personalityId, roomId);

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

  // Edit state management
  const [editingMessage, setEditingMessage] = useState<{ id: string; content: string } | null>(null);

  // Dialog states
  const [isRoomUsersOpen, setIsRoomUsersOpen] = useState(false);

  const [isDeleteRoomOpen, setIsDeleteRoomOpen] = useState(false);
  // Fetch room details and messages when IDs are available
  useEffect(() => {
    if (personalityId && roomId) {
      // Fetch room details
      dispatch(personalityRoomActions.getPersonalityRoom({ personalityId, roomId }));
      // Fetch messages for the room
      dispatch(fetchPersonalityMessages({ personalityId, roomId }));
    }
  }, [dispatch, personalityId, roomId]);

  // Auto-scroll to latest message
  useEffect(() => {
    setTimeout(() => {
      if (lastMessageRef.current) {
        lastMessageRef.current.scrollIntoView({
          behavior: "instant",
          block: "end",
        });
      }
    }, 100);
  }, [messages.length]);

  if (!personality || !room || (loading && messages.length === 0)) {
    return <Loading />;
  }

  const handleSendMessage = debounce<[string], void>((content) => {
    if (!personalityId || !roomId || !currentUser?.sub) return;

    if (editingMessage) {
      // Update existing message
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

  return (
    <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen">
      <div className="flex items-center justify-between mb-2 border-b pb-2 mobile-safe-top">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-lg lg:text-2xl font-bold">
          {room.name}
        </h1>
        <div className="flex-1" />
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

      <div className="flex flex-col flex-1 max-w-3xl self-center w-full">
        <div className="flex-1 overflow-y-auto relative">
          <div className="absolute top-0 left-0 right-0 bottom-0 flex flex-1 flex-col flex-nowrap max-h-full mx-auto overflow-y-auto">
            <div className="mt-4 w-full mx-auto relative z-10 flex flex-grow flex-col">
              <div className="flex-grow" />
              {messages.map((message, index) => (
                <div
                  key={message.id}
                  ref={index === messages.length - 1 ? lastMessageRef : null}
                >
                  <PersonalityChatItem
                    message={message}
                    personality={personality}
                    onEditMessage={handleEditMessage}
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
            className="w-full mx-auto mt-2 "
          />
        </div>
      </div>
    </div>
  );
}
