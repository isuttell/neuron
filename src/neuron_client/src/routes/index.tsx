import { useState, useEffect, useRef } from "react";
import { useAppSelector, useAppDispatch } from "../hooks";
import { CornerDownLeft, Upload } from "lucide-react";
import { AttachmentIndicator } from "@/components/AttachmentIndicator";
import { AudioRecorder } from "@/components/AudioRecorder";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { createThread } from "../actions/threadActions";
import { Spinner } from "@/components/ui/spinner";
import { useNavigate } from "react-router-dom";
import {
  getActivePersonalityId,
  getActivePersonality,
  setActivePersonality,
  getPersonalities,
} from "../slices/personalitiesSlice";
import logo from "@/assets/logo.svg";
import { useToast } from "@/hooks/use-toast";
import { PromptDropdown } from "@/components/PromptDropdown";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "../lib/utils";
import { fetchPersonalities } from "../actions/personalityActions";


export default function Index() {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | Blob | undefined>(undefined);
  const [isAudioRecording, setIsAudioRecording] = useState(false);
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setLoading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const personalities = useAppSelector(getPersonalities);

  const isSubmitDisabled =
    !activePersonalityId || (prompt.trim().length === 0 && !file);

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

  useEffect(() => {
    if (activePersonalityId) {
      // Small delay to ensure DOM is updated after personality selection
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  }, [activePersonalityId]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }

    if (isSubmitDisabled || isLoading) {
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
    <div className="flex flex-1 p-2 sm:p-4 ipad-top-spacing flex-col justify-center items-center flex-nowrap min-h-screen overflow-auto gap-2 relative">
      <SidebarTrigger className="m-2 size-10 absolute left-2 top-2" />
      <div className="flex flex-col w-full h-full justify-center items-center">
        <div className="flex justify-center items-center m-4 sm:m-6">
          <img src={logo} alt="Neuron" className="w-20 sm:w-[120px]" />
        </div>
        <div className="flex flex-col gap-2 max-w-[768px] mx-auto w-full">
          <form className="" onSubmit={handleSubmit}>
            <Label htmlFor="prompt" className="sr-only">
              Prompt
            </Label>
            <div className="space-y-2">
              <Textarea
                ref={textareaRef}
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
            <div className="flex flex-row flex-nowrap items-center gap-2 pt-2">
              <Button
                type="button"
                size="sm"
                variant={file ? "default" : "outline"}
                className="size-10 gap-1.5 flex-shrink-0"
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
                className="size-10 flex-shrink-0"
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
              <div className="flex-1" />
              <Button
                onClick={() => handleSubmit()}
                type="submit"
                size="sm"
                disabled={isSubmitDisabled}
                className={cn(
                  "size-10 flex-shrink-0",
                  isLoading && "cursor-progress",
                  isSubmitDisabled
                    ? "bg-muted text-muted-foreground cursor-not-allowed"
                    : "bg-accent text-accent-foreground"
                )}
              >
                {isLoading ? (
                  <Spinner className="size-3.5" />
                ) : (
                  <CornerDownLeft className="size-3.5" />
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
