import { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "../hooks";
import { createThread } from "../actions/threadActions";
import { useNavigate, useParams } from "react-router-dom";
import {
  getPersonality,
  getPersonalities,
  getDefaultPersonality,
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
import { getCurrentUser, getSelectedPersonalityId, getModePreference, setModePreference } from "../slices/appSlice";
import PersonalitySelector from "../components/PersonalitySelector";

export default function Index() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { personalityId } = useParams();
  const [isLoading, setLoading] = useState(false);
  const modePreference = useAppSelector(getModePreference);
  const isChatMode = modePreference === 'chat';
  const selectedPersonality = useAppSelector(
    (state) => personalityId ? getPersonality(state, personalityId) : undefined
  );
  const personalities = useAppSelector(getPersonalities);
  const isConnected = useAppSelector(getConnectionStatus);
  const currentUser = useAppSelector(getCurrentUser);
  const selectedPersonalityId = useAppSelector(getSelectedPersonalityId);
  const defaultPersonality = useAppSelector(getDefaultPersonality);

  const personalitiesLoading = useAppSelector(
    (state) => state.personalities.loading
  );

  useEffect(() => {
    dispatch(fetchPersonalities());
  }, [dispatch]);

  // Navigate to selected personality if no personality in URL but one is saved, or fallback to default
  useEffect(() => {
    if (!personalitiesLoading && personalities.length > 0 && !personalityId) {
      // First try the sticky personality
      if (selectedPersonalityId) {
        const personalityExists = personalities.some(p => p.id === selectedPersonalityId);
        if (personalityExists) {
          navigate(`/${selectedPersonalityId}`);
          return;
        }
      }

      // Fallback to default personality if no sticky personality or it doesn't exist
      if (defaultPersonality) {
        navigate(`/${defaultPersonality.id}`);
      }
    }
  }, [personalities, personalitiesLoading, personalityId, selectedPersonalityId, defaultPersonality, navigate]);

  // Redirect to personalities page if personalityId in URL doesn't exist
  useEffect(() => {
    if (!personalitiesLoading && personalities.length > 0 && personalityId) {
      const personalityExists = personalities.some(p => p.id === personalityId);
      if (!personalityExists) {
        navigate('/personalities');
      }
    }
  }, [personalities, personalitiesLoading, personalityId, navigate]);


  const handleSubmit = (prompt: string, file?: File | Blob) => {
    if (!personalityId || isLoading) {
      return;
    }

    setLoading(true);

    if (isChatMode) {
      // Chat mode: Create personality room and redirect
      dispatch(
        createPersonalityRoom({
          personalityId: personalityId,
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
                personalityId: personalityId,
                roomId: personality_room.id,
                content: prompt,
                userId: currentUser.sub,
                file,
              })
            );
          }
          navigate(`/personality/${personalityId}/room/${personality_room.id}`);
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
          personalityId: personalityId,
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
            disabled={!personalityId || !isConnected}
            isLoading={isLoading}
            placeholder={
              !isConnected
                ? "WebSocket disconnected - please wait for reconnection"
                : selectedPersonality
                ? "Type your prompt here..."
                : "Select a personality first"
            }
            personalityId={personalityId}
          >
            <div className="flex items-center gap-4">
              <PersonalitySelector />
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="mode-switch"
                  className={`text-sm ${isChatMode ? '' : 'opacity-50'} text-muted-foreground transition-opacity`}
                >
                  Chat
                </Label>
                <Switch
                  id="mode-switch"
                  checked={!isChatMode}
                  onCheckedChange={(checked) => dispatch(setModePreference(checked ? 'agent' : 'chat'))}
                  disabled={!personalityId || !isConnected}
                />
                <Label
                  htmlFor="mode-switch"
                  className={`text-sm ${isChatMode ? 'opacity-50' : ''} text-muted-foreground transition-opacity`}
                >
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
