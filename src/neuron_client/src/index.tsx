import { useState } from "react";
import { useAppSelector, useAppDispatch } from "./hooks";
import { CornerDownLeft, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { createThread } from "./actions/threadActions";
import { Spinner } from "@/components/ui/spinner";
import { useNavigate, Link } from "react-router-dom";
import {
  getActivePersonalityId,
  getActivePersonality,
} from "./slices/personalitiesSlice";
import logo from "@/assets/logo.svg";
import { useToast } from "@/hooks/use-toast";
import { RootState } from "./store";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";

const selectRecentThreads = (state: RootState) => {
  // Get the latest AI message timestamp for each thread
  const threadLastAiMessages = state.messages.messages
    .filter((message) => message.type === "ai")
    .reduce((acc, message) => {
      if (
        !acc[message.thread_id] ||
        (message.created_at ?? 0) > (acc[message.thread_id] ?? 0)
      ) {
        acc[message.thread_id] = message.created_at ?? 0;
      }
      return acc;
    }, {} as Record<string, number>);

  // Sort threads using the latest AI message timestamps
  return Object.values(state.threads.threads)
    .filter(
      (thread) =>
        threadLastAiMessages[thread.id] &&
        thread.updated_at > Date.now() - 1000 * 60 * 60
    ) // Only show threads with AI messages
    .sort(
      (a, b) =>
        (threadLastAiMessages[b.id] ?? 0) - (threadLastAiMessages[a.id] ?? 0)
    );
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
    <div className="flex flex-1 p-4 flex-col justify-center items-center flex-nowrap max-h-screen overflow-auto gap-2">
      <div className="flex flex-col w-full">
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
                {recentThreads.map((thread) => (
                  <Link
                    key={thread.id}
                    to={`/thread/${thread.id}`}
                    className="border-b border-border pb-2 last:border-b-0"
                  >
                    <div className="flex flex-row gap-2">
                      <div className="line-clamp-2 text-sm">{thread.name}</div>
                      <div className="text-sm text-muted-foreground">
                        <FuzzyTimeAgo timestamp={thread.created_at} />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
