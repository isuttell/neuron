import { useEffect, useState } from "react";
import { Trash } from "lucide-react";
import { useParams, useNavigate } from "react-router-dom";
import { useAppSelector, useAppDispatch } from "../hooks";
import { CornerDownLeft } from "lucide-react";
import { shallowEqual } from "react-redux";
import { RootState } from "../store";
import { Button } from "@/components/ui/button";
import Loading from "@/lib/loading";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { getSocket } from "../slices/socketSlice";
import { getActiveProviderId } from "../slices/providersSlice";
import { Spinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import { setActivePersonality } from "../slices/personalitiesSlice";

const selectPersonality = (state: RootState, personalityId?: string) =>
  state.personalities.personalities.find((per) => per.id === personalityId);

export default function Personality() {
  const socket = useAppSelector(getSocket);
  const [updatedContext, setUpdatedContext] = useState("");
  const activeProviderId = useAppSelector(getActiveProviderId);
  const [updatedName, setUpdatedName] = useState("");
  const [prompt, setPrompt] = useState("");
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const [isLoading, setIsLoading] = useState(false);
  const { personalityId } = useParams();
  const personality = useAppSelector(
    (state) => selectPersonality(state, personalityId),
    shallowEqual
  );
  useEffect(() => {
    if (!personality) {
      return;
    }
    setUpdatedContext(personality.context);
    setUpdatedName(personality.name);
  }, [personality?.id, personality?.context, personality?.name]);

  const handleSave = (e: React.FormEvent) => {
    if (!personality) {
      return;
    }
    e.preventDefault();
    dispatch({
      type: "socket/UpdatePersonality",
      id: personality.id,
      name: updatedName,
      context: updatedContext,
      memory: personality.memory,
    });
  };

  const handleSubmitPrompt = (
    e:
      | React.FormEvent<HTMLFormElement>
      | React.FormEvent<HTMLButtonElement>
      | React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    e.preventDefault();
    if (
      !socket ||
      prompt.trim().length === 0 ||
      !personality?.id ||
      !activeProviderId
    ) {
      return;
    }
    socket.sendMessage({
      type: "PostPersonalityPrompt",
      context: updatedContext,
      prompt,
      provider_id: activeProviderId,
    });
    setIsLoading(true);
    socket.once("personality_prompt_response", (data) => {
      setUpdatedContext(data.context);
      setIsLoading(false);
      setPrompt("");
    });
  };

  if (!personality) {
    return <Loading />;
  }

  const isActive = activePersonalityId === personality.id;

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto gap-2">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">
          {personality.name}
          {activePersonalityId === personality.id && (
            <span className="ml-2 text-xs text-muted-foreground">
              (active personality)
            </span>
          )}
        </h1>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            dispatch({
              type: "socket/DeletePersonality",
              personality_id: personality.id,
            });
            navigate("/");
          }}
        >
          <Trash className="size-4" />
          <span className="sr-only">Delete</span>
        </Button>
      </div>
      <div className="flex-1 flex flex-col flex-nowrap">
        <div className="flex w-full flex-1 flex-col flex-nowrap whitespace-pre-wrap max-w-[1170px] mx-auto">
          <div>
            <Label htmlFor="name" className="sr-only">
              Name
            </Label>
            <Input
              id="name"
              placeholder="Name"
              className="ring-offset-background flex-1 focus-visible:ring-offset-2 flex min-h-[60px] w-full rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4 mb-2"
              value={updatedName}
              onChange={(e) => setUpdatedName(e.target.value)}
            />
          </div>
          <div className="flex-1 flex">
            <Label htmlFor="context" className="sr-only">
              Context
            </Label>
            <Textarea
              id="context"
              placeholder="Context"
              disabled={isLoading}
              className="ring-offset-background flex-1 focus-visible:ring-offset-2 flex min-h-[60px] w-full rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4"
              value={updatedContext}
              onChange={(e) => setUpdatedContext(e.target.value)}
            />
          </div>
        </div>
      </div>
      <div className="bottom-0">
        <form
          className="flex flex-col gap-2 max-w-[1170px] mx-auto"
          onSubmit={handleSubmitPrompt}
        >
          <Label htmlFor="prompt" className="sr-only">
            Prompt
          </Label>
          <Textarea
            id="prompt"
            placeholder="Type your prompt here..."
            className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4"
            value={prompt}
            disabled={isLoading}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                handleSubmitPrompt(e);
              }
            }}
          />
          <div className="flex flex-row gap-2 pt-2">
            <Button
              className="ml-auto gap-1.5"
              variant={isActive ? "default" : "secondary"}
              onClick={() => {
                dispatch(
                  setActivePersonality(isActive ? undefined : personality.id)
                );
                if (!isActive) {
                  dispatch({
                    type: "socket/GetThreads",
                    personality_id: personality.id,
                  });
                }
              }}
            >
              {isActive ? "Deactivate" : "Activate"}
            </Button>
            <div className="flex-1" />
            <Button
              onClick={handleSubmitPrompt}
              type="submit"
              size="sm"
              disabled={
                isLoading || !activeProviderId || prompt.trim().length === 0
              }
              className="ml-auto gap-1.5"
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
            <Button
              onClick={() => {
                setUpdatedContext(personality.context);
                setUpdatedName(personality.name);
              }}
              type="reset"
              size="sm"
              variant="destructive"
              disabled={
                isLoading ||
                (personality?.name === updatedName &&
                  personality?.context === updatedContext)
              }
              className="ml-auto gap-1.5"
            >
              Reset
            </Button>
            <Button
              onClick={handleSave}
              type="button"
              size="sm"
              disabled={
                isLoading ||
                (personality?.name === updatedName &&
                  personality?.context === updatedContext)
              }
              className="ml-auto gap-1.5"
            >
              Save
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
