import React, { useState, useEffect } from "react";
import { UserPen } from "lucide-react";
import { useAppDispatch } from "../hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Personality } from "../slices/personalitiesSlice.d";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import { useNavigate } from "react-router-dom";
import {
  createPersonality,
  updatePersonality,
  deletePersonality,
} from "../actions/personalityActions";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ToolsetSelector from "../components/ToolsetSelector";

interface EditPersonalityDialogProps {
  personality?: Personality;
  default_tools?: string[];
  triggerOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  open?: boolean;
  trigger?: React.ReactNode;
}

interface ApiError extends Error {
  message: string;
}

export default function EditPersonalityDialog({
  personality,
  default_tools = ["image", "search", "tts"],
  triggerOpen,
  onOpenChange: externalOnOpenChange,
  open: controlledOpen,
  trigger,
}: EditPersonalityDialogProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);

  // Use controlled open if provided, otherwise use internal state
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;

  const handleOpenChange = (newOpen: boolean) => {
    if (!isControlled) {
      setUncontrolledOpen(newOpen);
    }
    externalOnOpenChange?.(newOpen);
  };
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState(personality?.name || "");
  const [description, setDescription] = useState(
    personality?.description || ""
  );
  const [context, setContext] = useState(personality?.context || "");

  const [logo, setLogo] = useState(personality?.logo || "");
  const [tool_set, setToolSet] = useState<string[]>(
    personality?.tool_set ? personality.tool_set.split("+") : []
  );
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) {
      return;
    }
    setLoading(true);
    try {
      if (personality) {
        await dispatch(
          updatePersonality({
            id: personality.id,
            name,
            description,
            context,
            logo,
            memory: personality.memory,
            tool_set: tool_set.length > 0 ? tool_set.join("+") : undefined,
          })
        ).unwrap();
      } else {
        const body = await dispatch(
          createPersonality({
            name,
            description,
            context,
            memory: "",
            logo,
            tool_set: tool_set.length > 0 ? tool_set.join("+") : undefined,
          })
        ).unwrap();

        navigate(`/personality/${body.personality.id}/edit`);
      }
      handleOpenChange(false);
    } catch (error: unknown) {
      const apiError = error as ApiError;
      console.log(apiError);
      toast.error("Failed to save personality", {
        description: apiError?.message || "An unexpected error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.FormEvent) => {
    if (!personality) {
      return;
    }
    e.preventDefault();
    await dispatch(deletePersonality(personality.id));
    handleOpenChange(false);
  };

  useEffect(() => {
    if (personality) {
      setName(personality.name || "");
      setContext(personality.context || "");
      setToolSet(personality.tool_set ? personality.tool_set.split("+") : []);
      setDescription(personality.description || "");
      setLogo(personality.logo || "");
    } else {
      setName("");
      setContext("");
      setToolSet([]);
      setDescription("");
      setLogo("");
    }
  }, [personality, open]);

  useEffect(() => {
    if (triggerOpen !== undefined && !isControlled) {
      setUncontrolledOpen(triggerOpen);
    }
  }, [triggerOpen, isControlled]);
  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {trigger !== undefined ? (
        trigger
      ) : (
        <Tooltip>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon">
                <UserPen className="m-3" />
                <span className="sr-only">
                  Edit Personality Details
                </span>
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>
            Edit Personality Details
          </TooltipContent>
        </Tooltip>
      )}
      <DialogContent className="max-w-[768px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader className="mb-4">
            <DialogTitle>
              Edit Personality Details
            </DialogTitle>
          </DialogHeader>
          <div className="mb-4">
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name"
            />
          </div>
          <div className="mb-4">
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description"
              rows={4}
            />
          </div>
          <div className="mb-4">
            <Input
              type="text"
              value={logo}
              onChange={(e) => setLogo(e.target.value)}
              placeholder="Logo URL"
            />
          </div>
          <div className="mb-4">
            <Textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Context"
              rows={10}
            />
          </div>
          <ToolsetSelector
            className="mb-4"
            value={tool_set}
            defaultValue={default_tools}
            onChange={setToolSet}
          />
          <DialogFooter className="flex justify-end">
            <Button
              variant="destructive"
              onClick={handleDelete}
              type="submit"
              className="ml-2"
            >
              Delete
            </Button>
            <div className="flex-1" />
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSubmit}
              type="submit"
              disabled={loading}
              className="ml-2"
            >
              {loading ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
