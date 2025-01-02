import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  fetchPrompts,
  createPrompt,
  updatePrompt,
  deletePrompt,
  selectPrompts,
  selectPromptsLoading,
} from "../slices/promptsSlice";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PromptForm } from "@/components/PromptForm";
import { Pencil, Trash2 } from "lucide-react";
import { getActivePersonalityId } from "@/slices/personalitiesSlice";
import { useToast } from "../hooks/use-toast";
import { Spinner } from "@/components/ui/spinner";
import { SidebarTrigger } from "@/components/ui/sidebar";
export default function PromptsPage() {
  const dispatch = useAppDispatch();
  const { toast } = useToast();
  const prompts = useAppSelector(selectPrompts);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const isLoading = useAppSelector(selectPromptsLoading);
  const [isUpdating, setIsUpdating] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  useEffect(() => {
    if (activePersonalityId) {
      dispatch(fetchPrompts(activePersonalityId));
    }
  }, [activePersonalityId]);

  const handleCreate = async (values: { name: string; text: string }) => {
    setIsUpdating(true);
    setIsCreateOpen(false);
    try {
      await dispatch(
        createPrompt({ ...values, personality_id: activePersonalityId })
      );
      setIsUpdating(false);
      toast({
        title: "Prompt created",
      });
    } catch (error) {
      toast({
        title: "Failed to create prompt",
        variant: "destructive",
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleUpdate = async (values: { name: string; text: string }) => {
    if (selectedPrompt) {
      setIsUpdating(true);
      setIsCreateOpen(false);
      try {
        await dispatch(
          updatePrompt({
            id: selectedPrompt,
            personality_id: activePersonalityId,
            ...values,
          })
        );
        setSelectedPrompt(null);
        toast({
          title: "Prompt updated",
        });
      } catch (error) {
        toast({
          title: "Failed to update prompt",
          variant: "destructive",
        });
      } finally {
        setIsUpdating(false);
      }
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this prompt?")) {
      setIsUpdating(true);
      try {
        await dispatch(deletePrompt(id));
        setIsUpdating(false);
        toast({
          title: "Prompt deleted",
        });
      } catch (error) {
        toast({
          title: "There was an error deleting the prompt",
          variant: "destructive",
        });
      } finally {
        setIsUpdating(false);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6 max-w-screen-md">
      <div className="flex justify-between items-center">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-2xl font-bold">Prompts</h1>
        <div className="flex-1" />
        <Button onClick={() => setIsCreateOpen(true)}>Create New Prompt</Button>
      </div>

      <div className="space-y-4">
        {prompts.map((prompt) => (
          <div
            key={prompt.id}
            className="p-4 border rounded-lg flex justify-between items-start"
          >
            <div className="space-y-2">
              <h3 className="font-medium">{prompt.name}</h3>
              <p className="text-sm text-gray-600">{prompt.text}</p>
            </div>
            <div className="flex space-x-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedPrompt(prompt.id)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleDelete(prompt.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))}
        {prompts.length === 0 && (
          <div className="p-4 flex justify-center items-center">
            <p className="text-sm text-gray-600">No saved prompts</p>
          </div>
        )}
      </div>

      {/* Edit Dialog */}
      <Dialog
        open={!!selectedPrompt}
        onOpenChange={() => setSelectedPrompt(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Prompt</DialogTitle>
          </DialogHeader>
          {selectedPrompt && (
            <PromptForm
              prompt={prompts.find((p) => p.id === selectedPrompt)}
              onSubmit={handleUpdate}
              onCancel={() => setSelectedPrompt(null)}
              disabled={isUpdating}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Prompt</DialogTitle>
          </DialogHeader>
          <PromptForm
            onSubmit={handleCreate}
            onCancel={() => setIsCreateOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
