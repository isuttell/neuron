import React, { useState } from "react";
import { Plus } from "lucide-react";
import { useAppDispatch } from "../hooks";
import { Button } from "@/components/ui/button";
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
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { generatePersonality } from "../actions/personalityActions";

interface CreatePersonalityDialogProps {
  onOpenChange?: (open: boolean) => void;
  open?: boolean;
  trigger?: React.ReactNode;
}

interface ApiError extends Error {
  message: string;
}

export default function CreatePersonalityDialog({
  onOpenChange: externalOnOpenChange,
  open: controlledOpen,
  trigger,
}: CreatePersonalityDialogProps) {
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
  const [prompt, setPrompt] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || !prompt.trim()) {
      return;
    }

    setLoading(true);
    try {
      // Call the new generate endpoint using Redux action
      const body = await dispatch(
        generatePersonality({
          prompt: prompt.trim(),
        })
      ).unwrap();

      // Navigate to the edit page for the new personality
      navigate(`/personality/${body.personality.id}`);

      toast.success("Personality created successfully!");
      handleOpenChange(false);

      // Reset form
      setPrompt("");
    } catch (error: unknown) {
      const apiError = error as ApiError;
      console.log(apiError);
      toast.error("Failed to create personality", {
        description: apiError?.message || "An unexpected error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {trigger !== undefined ? (
        trigger
      ) : (
        <Tooltip>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon">
                <Plus className="m-3" />
                <span className="sr-only">
                  Create New Personality
                </span>
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>
            Create New Personality
          </TooltipContent>
        </Tooltip>
      )}
      <DialogContent className="max-w-[768px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader className="mb-4">
            <DialogTitle>
              Create New Personality
            </DialogTitle>
          </DialogHeader>
          <div className="mb-4">
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the personality you want to create. For example: 'A helpful coding assistant that explains complex programming concepts in simple terms and provides practical examples with a dry sense of humor.'"
              rows={4}
              disabled={loading}
              className="min-h-[100px]"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
          </div>
          <DialogFooter className="flex justify-end">
            <DialogClose asChild>
              <Button type="button" variant="ghost" disabled={loading}>
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSubmit}
              type="submit"
              disabled={loading || !prompt.trim()}
              className="ml-2"
            >
              {loading ? (
                <>
                  <Spinner className="size-4 mr-2" />
                  Generating...
                </>
              ) : (
                "Generate Personality"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
