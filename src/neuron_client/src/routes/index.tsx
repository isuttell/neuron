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


export default function Index() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setLoading] = useState(false);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const personalities = useAppSelector(getPersonalities);

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

  const handleSubmit = (prompt: string, file?: File | Blob) => {
    if (!activePersonalityId || isLoading) {
      return;
    }

    setLoading(true);
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
            disabled={!activePersonalityId}
            isLoading={isLoading}
            placeholder={
              activePersonality
                ? "Type your prompt here..."
                : "Select a personality first"
            }
          >
            {activePersonality && (
              <div className="text-xs text-gray-600 pl-1">
                {activePersonality.name}
              </div>
            )}
          </MessageForm>
        </div>
      </div>
    </div>
  );
}
