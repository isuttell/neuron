import { Trash } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppDispatch } from "../hooks";
import { toast } from "sonner";
import { deletePersonality } from "../actions/personalityActions";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface DeletePersonalityDialogProps {
  personalityId: string;
  personalityName?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: React.ReactNode;
}

export default function DeletePersonalityDialog({
  personalityId,
  personalityName,
  open: controlledOpen,
  onOpenChange,
  trigger,
}: DeletePersonalityDialogProps) {
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
    onOpenChange?.(newOpen);
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
                <Trash className="m-3" />
                <span className="sr-only">Delete Personality</span>
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>Delete Personality</TooltipContent>
        </Tooltip>
      )}
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you absolutely sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete the personality
            {personalityName ? ` "${personalityName}"` : ""}.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="justify-end">
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </DialogClose>
          <Button
            type="button"
            variant="destructive"
            onClick={async () => {
              navigate("/");
              try {
                await dispatch(deletePersonality(personalityId));
                toast("Personality deleted");
              } catch (error) {
                toast.error("Failed to delete personality", {
                  description:
                    error instanceof Error
                      ? error.message
                      : "An unexpected error occurred",
                });
              }
            }}
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
