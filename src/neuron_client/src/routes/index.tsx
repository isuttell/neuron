import { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "../hooks";
import { createThread } from "../actions/threadActions";
import { useNavigate, Link } from "react-router-dom";
import {
  getActivePersonalityId,
  getActivePersonality,
  setActivePersonality,
} from "../slices/personalitiesSlice";
import logo from "@/assets/logo.svg";
import { useToast } from "@/hooks/use-toast";
import { RootState } from "../store";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import { fetchRecentThreads } from "../actions/threadActions";
import { StatusMessage } from "../messages/StatusMessage";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "../lib/utils";
import { fetchPersonalities } from "../actions/personalityActions";
import MessageForm from "../messages/MessageForm";

const selectRecentThreads = (state: RootState) => {
  const oneDayAgo = Date.now() - 1000 * 60 * 60 * 24; // 24 hours ago in milliseconds
  return Object.values(state.threads.threads)
    .sort((a, b) => Number(b.updated_at) - Number(a.updated_at))
    .filter((thread) => Number(thread.updated_at) > oneDayAgo) // Only show threads from last day
    .slice(0, 5)
    .map((thread) => ({
      ...thread,
      personality: state.personalities.personalities.find(
        (personality) => personality.id === thread.personality_id
      ),
    }));
};

export default function Index() {
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setLoading] = useState(false);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const recentThreads = useAppSelector(selectRecentThreads);

  useEffect(() => {
    dispatch(fetchPersonalities());
    dispatch(fetchRecentThreads());
  }, [dispatch]);


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
        toast({
          variant: "destructive",
          title: "Failed to create thread",
          description: error?.message || "An unexpected error occurred",
        });
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <div className="flex flex-1 p-2 sm:p-4 ipad-top-spacing flex-col justify-center items-center flex-nowrap min-h-screen overflow-auto gap-2 relative">
      <SidebarTrigger className="m-2 size-10 absolute left-2 top-2" />
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
          />
          {recentThreads.length > 0 ? (
            <>
              <div className="text-sm font-bold text-muted-foreground mt-6">
                Recent updates
              </div>
              <div className="flex flex-col gap-2 mt-2">
                {recentThreads.map((thread) => {
                  return (
                    <Link
                      key={thread.id}
                      to={`/thread/${thread.id}`}
                      className={cn(
                        "border-b border-border pb-2 last:pb-0 last:border-b-0"
                      )}
                      onClick={() => {
                        dispatch(setActivePersonality(thread.personality?.id));
                      }}
                    >
                      <div className="flex flex-col sm:flex-row gap-1 sm:gap-2 text-sm">
                        <div className="font-bold">
                          {thread.name || "Untitled"}
                        </div>
                        <div className="italic text-muted-foreground sentence-case">
                          from {thread.personality?.name || "Unknown"}
                        </div>
                        {thread.status !== "idle" ? (
                          <div className="text-muted-foreground font-bold">
                            <StatusMessage
                              status={thread.status}
                              tagClassName="border-b mb-[-1px]"
                            />
                          </div>
                        ) : null}
                        <div className="text-muted-foreground lowercase">
                          <FuzzyTimeAgo ago timestamp={thread.updated_at} />
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
