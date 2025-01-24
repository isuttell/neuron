import { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "../hooks";
import { CornerDownLeft, Upload } from "lucide-react";
import { AttachmentIndicator } from "@/components/AttachmentIndicator";
import { AudioRecorder } from "@/components/AudioRecorder";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { createThread } from "../actions/threadActions";
import { Spinner } from "@/components/ui/spinner";
import { useNavigate, Link } from "react-router-dom";
import {
  getActivePersonalityId,
  getActivePersonality,
  setActivePersonality,
  getPersonalities,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchPersonalities } from "../actions/personalityActions";

const selectRecentThreads = (state: RootState) => {
  return Object.values(state.threads.threads)
    .sort((a, b) => b.updated_at - a.updated_at)
    .filter((thread) => thread.updated_at > Date.now() - 1000 * 60 * 60 * 24) // Only show threads from last day
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
  const [file, setFile] = useState<File | Blob | undefined>(undefined);
  const [isAudioRecording, setIsAudioRecording] = useState(false);
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setLoading] = useState(false);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const recentThreads = useAppSelector(selectRecentThreads);
  const personalities = useAppSelector(getPersonalities);

  const personalitiesLoading = useAppSelector(
    (state) => state.personalities.loading
  );

  useEffect(() => {
    dispatch(fetchPersonalities());
    dispatch(fetchRecentThreads());
  }, []);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }

    if (!activePersonalityId || (prompt.trim().length === 0 && !file)) {
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

  const handleGreeting = () => {
    if (!activePersonalityId) return;

    setLoading(true);
    dispatch(
      createThread({
        personalityId: activePersonalityId,
        prompt,
        greeting: true,
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

  const handleAutoSend = (blob: Blob) => {
    if (!activePersonalityId) return;
    setLoading(true);
    dispatch(
      createThread({
        personalityId: activePersonalityId,
        prompt,
        greeting: false,
        file: blob,
      })
    )
      .unwrap()
      .then(({ thread }) => {
        navigate(`/thread/${thread.id}`);
        setFile(undefined);
        setPrompt("");
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
      setIsAudioRecording(false);
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
        <div className="flex justify-center items-center m-6">
          <img src={logo} alt="Neuron" className="w-[120px]" />
        </div>
        <div className="flex flex-col gap-2 max-w-[768px] mx-auto w-full">
          <form className="" onSubmit={handleSubmit}>
            <Label htmlFor="prompt" className="sr-only">
              Prompt
            </Label>
            <div className="space-y-2">
              <Textarea
                id="prompt"
                placeholder={
                  activePersonality
                    ? "Type your prompt here..."
                    : "Select a personality first"
                }
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
              {file && (
                <AttachmentIndicator
                  type={isAudioRecording ? "audio" : "file"}
                  name={file instanceof File ? file.name : undefined}
                  onRemove={() => {
                    setFile(undefined);
                    setIsAudioRecording(false);
                    toast({
                      title: "Attachment removed",
                    });
                  }}
                />
              )}
            </div>
            <div className="flex flex-row gap-2 pt-2">
              <Select
                value={activePersonalityId}
                onValueChange={(value) => dispatch(setActivePersonality(value))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue
                    placeholder={
                      personalitiesLoading
                        ? "Loading personalities..."
                        : "Select a personality"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {personalitiesLoading && personalities.length < 1 ? (
                    <div className="flex items-center justify-center p-2">
                      <Spinner className="size-4" />
                    </div>
                  ) : personalities.length === 0 ? (
                    <div className="text-sm text-muted-foreground text-center p-2">
                      No personalities found
                    </div>
                  ) : (
                    personalities
                      .slice()
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map((personality) => (
                        <SelectItem key={personality.id} value={personality.id}>
                          {personality.name}
                        </SelectItem>
                      ))
                  )}
                </SelectContent>
              </Select>
              <div className="flex-1" />
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={file ? "default" : "outline"}
                  className="size-10 gap-1.5"
                  disabled={isDisabled}
                  onClick={() => {
                    if (file) {
                      setFile(undefined);
                      setIsAudioRecording(false);
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
                <AudioRecorder
                  className="size-10"
                  disabled={isDisabled || !!file}
                  onRecordingComplete={(blob) => {
                    setFile(blob);
                    setIsAudioRecording(true);
                    toast({
                      title: "Recording sent",
                      description: "Starting new conversation",
                    });
                  }}
                  onAutoSend={handleAutoSend}
                />
              </div>
              <PromptDropdown
                disabled={isDisabled}
                onSelectPrompt={(promptText) => setPrompt(promptText)}
              />
              <input
                id="file-upload"
                type="file"
                className="hidden"
                onChange={handleFileUpload}
                accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.md,.txt,.csv,.srt,.vtt,.mp3,.wav,.mp4,.heic,.heif"
              />
              {!isLoading ? (
                <Button
                  onClick={handleGreeting}
                  type="button"
                  className="gap-1.5"
                  disabled={isDisabled}
                >
                  Get Started
                </Button>
              ) : null}
              <Button
                onClick={() => handleSubmit()}
                type="submit"
                disabled={isDisabled || (!prompt.trim().length && !file)}
                className="gap-1.5 bg-accent text-accent-foreground"
              >
                {isLoading ? (
                  <>
                    <Spinner className="size-3.5" />
                  </>
                ) : (
                  <>
                    Send
                    <CornerDownLeft className="size-3.5" />
                  </>
                )}
              </Button>
            </div>
          </form>
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
