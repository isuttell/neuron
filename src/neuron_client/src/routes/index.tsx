import { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "../hooks";
import { CornerDownLeft, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { createThread } from "../actions/threadActions";
import { Spinner } from "@/components/ui/spinner";
import { useNavigate, Link } from "react-router-dom";
import {
  getActivePersonalityId,
  getActivePersonality,
} from "../slices/personalitiesSlice";
import logo from "@/assets/logo.svg";
import { useToast } from "@/hooks/use-toast";
import { RootState } from "../store";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import { fetchRecentThreads } from "../actions/threadActions";
import { StatusMessage } from "../messages/StatusMessage";
import { PromptDropdown } from "@/components/PromptDropdown";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "../lib/utils";

const selectRecentThreads = (state: RootState) => {
  return Object.values(state.threads.threads)
    .sort((a, b) => b.updated_at - a.updated_at)
    .filter((thread) => thread.updated_at > Date.now() - 1000 * 60 * 60 * 12) // Only show threads from last day
    .slice(0, 5)
    .map((thread) => ({
      ...thread,
      personality: state.personalities.personalities.find(
        (personality) => personality.id === thread.personality_id
      ),
    }));
};

export default function Index() {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | undefined>(undefined);
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setLoading] = useState(false);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const recentThreads = useAppSelector(selectRecentThreads);

  useEffect(() => {
    dispatch(fetchRecentThreads());
  }, []);

  const handleSubmit = (greeting?: boolean) => {
    if (!activePersonalityId || (prompt.trim().length === 0 && !greeting)) {
      return;
    }
    setLoading(true);
    dispatch(
      createThread({
        personalityId: activePersonalityId,
        prompt,
        greeting,
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
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFile(file);
      toast({
        title: "Attachment added",
        description: `${file.name} has been added to the message`,
      });
    }
  };

  const isDisabled = !activePersonalityId || isLoading;

  return (
    <div className="flex flex-1 p-4 flex-col justify-center items-center flex-nowrap max-h-screen overflow-auto gap-2 relative">
      <SidebarTrigger className="m-2 size-10 absolute top-2 left-2" />
      <div className="flex flex-col w-full h-full justify-center items-center">
        <div className="flex justify-center items-center">
          <img src={logo} alt="Neuron" className="w-[120px]" />
        </div>
        <div className="flex flex-col gap-2 max-w-[768px] mx-auto w-full">
          {activePersonality ? (
            <div className="text-md text-center mb-6 font-bold">
              {activePersonality.name}
            </div>
          ) : (
            <div className="text-sm text-center mb-6">
              Select a personality to start chatting
            </div>
          )}
          <form
            className=""
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit();
            }}
          >
            <Label htmlFor="prompt" className="sr-only">
              Prompt
            </Label>
            <Textarea
              id="prompt"
              placeholder="Type your prompt here..."
              className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4"
              value={prompt}
              disabled={isDisabled}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
            />
            <div className="flex flex-row gap-2 pt-2 justify-end">
              <Button
                type="button"
                size="sm"
                variant={file ? "default" : "outline"}
                className="mr-2 gap-1.5"
                disabled={isDisabled}
                onClick={() => {
                  if (file) {
                    setFile(undefined);
                    toast({
                      title: "Attachment removed",
                    });
                  } else {
                    document.getElementById("file-upload")?.click();
                  }
                }}
              >
                <Upload className="size-3.5" />
              </Button>
              <PromptDropdown
                disabled={isDisabled}
                onSelectPrompt={(promptText) => setPrompt(promptText)}
              />
              <input
                id="file-upload"
                type="file"
                className="hidden"
                onChange={handleFileUpload}
                accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.md,.txt,.csv,.srt,.vtt,.mp3,.wav,.mp4"
              />
              {!isLoading ? (
                <Button
                  onClick={() => handleSubmit(true)}
                  type="submit"
                  className="gap-1.5"
                  disabled={isDisabled}
                >
                  Greet
                </Button>
              ) : null}
              <Button
                onClick={() => handleSubmit(false)}
                type="submit"
                disabled={isDisabled || prompt.trim().length === 0}
                className="gap-1.5 bg-primary text-primary-foreground"
              >
                {isLoading ? (
                  <>
                    <Spinner className="size-3.5" />
                  </>
                ) : (
                  <>
                    Prompt
                    <CornerDownLeft className="size-3.5" />
                  </>
                )}
              </Button>
            </div>
          </form>
          {recentThreads.length > 0 ? (
            <>
              <div className="text-sm font-bold text-muted-foreground">
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
                    >
                      <div className="flex flex-row gap-2 text-sm">
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
                          <FuzzyTimeAgo ago timestamp={thread.created_at} />
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
