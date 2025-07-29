import { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "../hooks";
import { createThread } from "../actions/threadActions";
import { useNavigate } from "react-router-dom";
import {
  getActivePersonalityId,
  getActivePersonality,
  setActivePersonality,
  getPersonalities,
} from "../slices/personalitiesSlice";
import logo from "@/assets/logo.svg";
import { toast } from "sonner";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { fetchPersonalities } from "../actions/personalityActions";
import MessageForm from "../messages/MessageForm";
import { getConnectionStatus } from "../slices/socketSlice";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { createPersonalityRoom } from "../actions/personalityRoomActions";
import { sendPersonalityMessage } from "../actions/personalityChatActions";
import { getCurrentUser } from "../slices/appSlice";
import PersonalitySelector from "../components/PersonalitySelector";

export default function Index() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setLoading] = useState(false);
  const [isChatMode, setIsChatMode] = useState(() => {
    // Load preference from localStorage, default to true (Chat mode)
    const saved = localStorage.getItem("neuron_mode_preference");
    return saved !== null ? saved === "chat" : true;
  });
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const personalities = useAppSelector(getPersonalities);
  const isConnected = useAppSelector(getConnectionStatus);
  const currentUser = useAppSelector(getCurrentUser);

  const personalitiesLoading = useAppSelector(
    (state) => state.personalities.loading
  );

  useEffect(() => {
    dispatch(fetchPersonalities());
  }, [dispatch]);

  // Clear activePersonalityId if it doesn't exist in the loaded personalities
  useEffect(() => {
    if (!personalitiesLoading && personalities.length > 0 && activePersonalityId) {
      const personalityExists = personalities.some(p => p.id === activePersonalityId);
      if (!personalityExists) {
        dispatch(setActivePersonality(undefined));
      }
    }
  }, [personalities, personalitiesLoading, activePersonalityId, dispatch]);

  // Save mode preference to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("neuron_mode_preference", isChatMode ? "chat" : "agent");
  }, [isChatMode]);

  const handleSubmit = (prompt: string, file?: File | Blob) => {
    if (!activePersonalityId || isLoading) {
      return;
    }

    setLoading(true);

    if (isChatMode) {
      // Chat mode: Create personality room and redirect
      dispatch(
        createPersonalityRoom({
          personalityId: activePersonalityId,
          data: {
            type: 'private'
          }
        })
      )
        .unwrap()
        .then(({ personality_room }) => {
          // Send the user's initial message to the room
          if (currentUser?.sub) {
            dispatch(
              sendPersonalityMessage({
                personalityId: activePersonalityId,
                roomId: personality_room.id,
                content: prompt,
                userId: currentUser.sub,
              })
            );
          }
          navigate(`/personality/${activePersonalityId}/room/${personality_room.id}`);
        })
        .catch((error) => {
          toast.error("Failed to create chat room", {
            description: error?.message || "An unexpected error occurred",
          });
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      // Agent mode: Create thread (existing behavior)
      dispatch(
        createThread({
          personalityId: activePersonalityId,
          prompt,
          greeting: false,
          file,
        })
      )
        .unwrap()
        .then(({ thread }) => {
          navigate(`/thread/${thread.id}`);
        })
        .catch((error) => {
          toast.error("Failed to create thread", {
            description: error?.message || "An unexpected error occurred",
          });
        })
        .finally(() => {
          setLoading(false);
        });
    }
  };

  return (
    <div className="flex flex-1 p-2 sm:p-4 ipad-top-spacing mobile-pwa-safe-top flex-col justify-center items-center flex-nowrap min-h-screen overflow-auto gap-2 relative">
      <SidebarTrigger className="m-2 size-10 absolute left-2 safe-trigger-top" />
      <div className="flex flex-col w-full h-full justify-center items-center">
        <div className="flex justify-center items-center m-4 sm:m-6">
          <img src={logo} alt="Neuron" className="w-20 sm:w-[120px]" />
        </div>
        <div className="flex flex-col gap-2 max-w-[768px] mx-auto w-full">
          <MessageForm
            onSubmit={handleSubmit}
            disabled={!activePersonalityId || !isConnected}
            isLoading={isLoading}
            placeholder={
              !isConnected
                ? "WebSocket disconnected - please wait for reconnection"
                : activePersonality
                ? "Type your prompt here..."
                : "Select a personality first"
            }
          >
            <div className="flex items-center gap-4">
              <PersonalitySelector />
              <div className="flex items-center gap-2">
                <Label htmlFor="mode-switch" className="text-sm text-muted-foreground">
                  Chat
                </Label>
                <Switch
                  id="mode-switch"
                  checked={!isChatMode}
                  onCheckedChange={(checked) => setIsChatMode(!checked)}
                  disabled={!activePersonalityId || !isConnected}
                />
                <Label htmlFor="mode-switch" className="text-sm text-muted-foreground">
                  Agent
                </Label>
              </div>
            </div>
          </MessageForm>
        </div>
      </div>
    </div>
  );
}
