import React, { useState, useEffect } from "react";
import { Edit } from "lucide-react";
import { useAppDispatch } from "../hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Thread } from "../types/thread";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import { updateThread } from "../actions/threadActions";
import { toast } from "sonner";
interface EditThreadFormProps {
  thread: Thread;
}

const EditThreadDialog: React.FC<EditThreadFormProps> = ({ thread }) => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(thread.name);
  const [context, setContext] = useState(thread.context);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setName(thread.name);
    setContext(thread.context);
  }, [thread.id, thread.name, thread.context]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await dispatch(updateThread({ id: thread.id, name, context }));
      setOpen(false);
      setLoading(false);
    } catch (error) {
      toast.error("Failed to save thread", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <Edit className="size-4" />
          <span className="sr-only">Edit</span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader className="mb-4">
            <DialogTitle>Edit Thread</DialogTitle>
          </DialogHeader>
          <div className="mb-4">
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Thread Name"
            />
          </div>
          <div className="mb-4">
            <Textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Context"
            />
          </div>
          <DialogFooter className="flex justify-end">
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSubmit}
              type="submit"
              className="ml-2"
              disabled={loading}
            >
              {loading ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EditThreadDialog;
