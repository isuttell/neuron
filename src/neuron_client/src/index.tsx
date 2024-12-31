import { useState } from "react";
import { useAppSelector, useAppDispatch } from "./hooks";
import { CornerDownLeft, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { createThread } from "./actions/threadActions";
import { Spinner } from "@/components/ui/spinner";
import { useNavigate } from "react-router-dom";
import {
  getActivePersonalityId,
  getActivePersonality,
} from "./slices/personalitiesSlice";
import logo from "@/assets/logo.svg";
import { useToast } from "@/hooks/use-toast";
export default function Index() {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState<File | undefined>(undefined);
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setLoading] = useState(false);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
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
                accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.md,.txt,.csv"
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
        </div>
      </div>
    </div>
  );
}
