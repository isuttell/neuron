import { Trash } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAppDispatch } from "../hooks";
import { useToast } from "../hooks/use-toast";
import { deleteThread } from "../actions/threadActions";
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

interface DeleteThreadButtonProps {
  threadId: string;
}

export default function DeleteThreadButton({
  threadId,
}: DeleteThreadButtonProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { toast } = useToast();

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <Trash className="size-4" />
          <span className="sr-only">Delete</span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you absolutely sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete your
            thread and remove your data from our servers.
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
                await dispatch(deleteThread(threadId));
                toast({
                  title: "Thread deleted",
                });
              } catch (error: any) {
                toast({
                  variant: "destructive",
                  title: "Failed to delete thread",
                  description: error?.message || "An unexpected error occurred",
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
