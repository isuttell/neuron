import { useEffect, useState } from "react";
import { Trash, ArrowLeft } from "lucide-react";
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
import { Spinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import { setActivePersonality } from "../slices/personalitiesSlice";
import {
  fetchPersonality,
  updatePersonality,
  deletePersonality,
} from "../actions/personalityActions";
import EditPersonalityDialog from "../personalities/EditPersonalityDialog";
import PersonalityUsersDialog from "../personalities/PersonalityUsersDialog";
import { toast } from "sonner";
import { api } from "@/lib/api";
import ToolsetSelector from "../components/ToolsetSelector";

const selectPersonality = (state: RootState, personalityId?: string) =>
  state.personalities.personalities.find((per) => per.id === personalityId);

export default function Personality() {
  const [updatedContext, setUpdatedContext] = useState("");
  const [updatedName, setUpdatedName] = useState("");
  const [updatedToolSet, setUpdatedToolSet] = useState<string[]>([]);
  const [prompt, setPrompt] = useState("");
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { personalityId } = useParams();
  const personality = useAppSelector(
    (state) => selectPersonality(state, personalityId),
    shallowEqual
  );

  useEffect(() => {
    if (!personalityId) {
      return;
    }
    dispatch(fetchPersonality(personalityId));
  }, [personalityId, dispatch]);

  useEffect(() => {
    if (!personality) {
      return;
    }
    setUpdatedContext(personality.context);
    setUpdatedName(personality.name);
    setUpdatedToolSet(personality.tool_set ? personality.tool_set.split("+") : []);
  }, [personality]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!personality || isLoading) {
      return;
    }
    setIsSaving(true);
    try {
      await dispatch(
        updatePersonality({
          id: personality.id,
          name: updatedName,
          description: personality.description,
          context: updatedContext,
          memory: personality.memory,
          tool_set: updatedToolSet.length > 0 ? updatedToolSet.join("+") : undefined,
          logo: personality.logo,
        })
      ).unwrap();
      toast.success("Personality saved successfully");
    } catch {
      toast.error("Failed to save personality");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitPrompt = async (
    e:
      | React.FormEvent<HTMLFormElement>
      | React.FormEvent<HTMLButtonElement>
      | React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    e.preventDefault();
    if (prompt.trim().length === 0 || !personality?.id) {
      return;
    }

    try {
      setIsLoading(true);
      const data = await api.post<{ context: string }>(
        `/personalities/${personality.id}/context`,
        {
          context: updatedContext,
          prompt,
        }
      );
      setUpdatedContext(data.context);
      setPrompt("");
      toast("Context updated");
    } catch {
      toast.error("Failed to update personality context");
    } finally {
      setIsLoading(false);
    }
  };

  if (!personality) {
    return <Loading />;
  }

  const isActive = activePersonalityId === personality.id;

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto gap-2">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">
          <Button
            className="mr-4"
            variant="ghost"
            size="icon"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="size-4" />
          </Button>
          Edit {personality.name}
          {activePersonalityId === personality.id && (
            <span className="ml-2 text-xs text-muted-foreground">
              (active personality)
            </span>
          )}
        </h1>
        <div className="flex-1" />
        <PersonalityUsersDialog personalityId={personality.id} />
        <EditPersonalityDialog personality={personality} />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            navigate("/");
            dispatch(deletePersonality(personality.id));
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
          <ToolsetSelector
            className="mb-2"
            value={updatedToolSet}
            onChange={setUpdatedToolSet}
          />
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
          <div className="flex gap-2">
            <Label htmlFor="prompt" className="sr-only">
              Prompt
            </Label>
            <Textarea
              id="prompt"
              placeholder="Ask Neuron to update the personality context for you..."
              className="flex-1 min-h-[60px] rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4"
              value={prompt}
              disabled={isLoading}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  handleSubmitPrompt(e);
                }
              }}
            />
            <Button
              onClick={handleSubmitPrompt}
              type="submit"
              size="default"
              disabled={isLoading || prompt.trim().length === 0}
              className="self-start"
            >
              {isLoading ? (
                <>
                  <Spinner className="size-4" />
                </>
              ) : (
                <>
                  Prompt
                  <CornerDownLeft className="size-4 ml-1" />
                </>
              )}
            </Button>
          </div>
          <div className="flex flex-row gap-2 pt-2">
            <Button
              className="gap-1.5"
              variant={isActive ? "default" : "secondary"}
              onClick={() => {
                dispatch(
                  setActivePersonality(isActive ? undefined : personality.id)
                );
                toast.success(
                  isActive ? "Personality deactivated" : "Personality activated"
                );
              }}
            >
              {isActive ? "Deactivate" : "Activate"}
            </Button>
            <div className="flex-1" />
            <Button
              onClick={() => {
                setUpdatedContext(personality.context);
                setUpdatedName(personality.name);
                setUpdatedToolSet(personality.tool_set ? personality.tool_set.split("+") : []);
                toast("Changes reset");
              }}
              type="reset"
              size="sm"
              variant="destructive"
              disabled={
                isLoading ||
                (personality?.name === updatedName &&
                  personality?.context === updatedContext &&
                  personality?.tool_set === (updatedToolSet.length > 0 ? updatedToolSet.join("+") : ""))
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
                isSaving ||
                isLoading ||
                (personality?.name === updatedName &&
                  personality?.context === updatedContext &&
                  personality?.tool_set === (updatedToolSet.length > 0 ? updatedToolSet.join("+") : ""))
              }
              className="ml-auto gap-1.5"
            >
              {isSaving ? (
                <>
                  <Spinner className="size-3.5" />
                </>
              ) : (
                <>Save</>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
