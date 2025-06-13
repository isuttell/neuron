import { useEffect, useState, useMemo } from "react";
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
import { CornerDownLeft, Pencil, FilePlus, Trash2 } from "lucide-react";
import {
  setActivePersonality,
  getActivePersonalityId,
} from "@/slices/personalitiesSlice";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/spinner";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { getPersonalities } from "@/slices/personalitiesSlice";
import { createThread } from "../actions/threadActions";
import { useNavigate } from "react-router-dom";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export default function PromptsPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const prompts = useAppSelector(selectPrompts);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const isLoading = useAppSelector(selectPromptsLoading);
  const [isUpdating, setIsUpdating] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const personalities = useAppSelector(getPersonalities);
  const personalitiiesMap = useMemo(
    () => new Map(personalities.map((p) => [p.id, p])),
    [personalities]
  );

  useEffect(() => {
    dispatch(fetchPrompts());
  }, [dispatch]);

  const handleCreate = async (values: {
    name: string;
    text: string;
    personalityId?: string;
  }) => {
    setIsUpdating(true);
    setIsCreateOpen(false);
    try {
      await dispatch(
        createPrompt({
          name: values.name,
          text: values.text,
          personality_id: values.personalityId || activePersonalityId,
        })
      );
      setIsUpdating(false);
      toast("Prompt created");
    } catch {
      toast.error("Failed to create prompt");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleUpdate = async (values: {
    name: string;
    text: string;
    personalityId?: string;
  }) => {
    if (selectedPrompt) {
      setIsUpdating(true);
      setIsCreateOpen(false);
      try {
        await dispatch(
          updatePrompt({
            id: selectedPrompt,
            personality_id: values.personalityId || activePersonalityId,
            name: values.name,
            text: values.text,
          })
        );
        setSelectedPrompt(null);
        toast("Prompt updated");
      } catch {
        toast.error("Failed to update prompt");
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
        toast("Prompt deleted");
      } catch {
        toast.error("There was an error deleting the prompt");
      } finally {
        setIsUpdating(false);
      }
    }
  };

  const groupedPrompts = useMemo(() => {
    const groups: { [key: string]: typeof prompts } = {};
    prompts.forEach((prompt) => {
      const personalityId = prompt.personality_id || "default";
      if (!groups[personalityId]) {
        groups[personalityId] = [];
      }
      groups[personalityId].push(prompt);
    });
    return groups;
  }, [prompts]);

  if (isLoading && prompts.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex flex-1 p-4 ipad-top-spacing mobile-pwa-safe-top flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-2xl font-bold">Prompts</h1>
        <div className="flex-1" />
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" onClick={() => setIsCreateOpen(true)}>
              <FilePlus className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Create new prompt</TooltipContent>
        </Tooltip>
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="space-y-8 max-w-[768px] mx-auto">
          {Object.entries(groupedPrompts)
            .sort(([a], [b]) => {
              const nameA = personalitiiesMap.get(a)?.name || "";
              const nameB = personalitiiesMap.get(b)?.name || "";
              return nameA.localeCompare(nameB);
            })
            .map(([personalityId, personalityPrompts]) => (
              <div key={personalityId} className="space-y-4">
                <div className="flex border-b pb-2 px-4">
                  {personalitiiesMap.get(personalityId)?.logo ? (
                    <img
                      src={personalitiiesMap
                        .get(personalityId)
                        ?.logo?.replace(/\.[^.]+$/, `_t.webp`)}
                      alt={personalitiiesMap.get(personalityId)?.name}
                      className="size-8 rounded-sm mr-4 max-w-8 max-h-8 overflow-hidden bg-muted"
                    />
                  ) : null}
                  <h2 className="text-xl font-semibold ">
                    {personalitiiesMap.get(personalityId)?.name || "General"}
                  </h2>
                  <div className="flex-1" />
                  {personalitiiesMap.get(personalityId) ? (
                    <Button
                      variant={
                        activePersonalityId === personalityId
                          ? "default"
                          : "outline"
                      }
                      onClick={() => {
                        dispatch(
                          setActivePersonality(
                            personalityId !== activePersonalityId
                              ? personalityId
                              : undefined
                          )
                        );
                      }}
                    >
                      {activePersonalityId === personalityId
                        ? "Deactivate"
                        : "Activate"}
                    </Button>
                  ) : null}
                </div>
                <div className="space-y-4">
                  {personalityPrompts
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((prompt) => (
                      <div
                        key={prompt.id}
                        className="p-4 border rounded-lg flex justify-between items-start"
                      >
                        <div className="space-y-2 flex justify-center items-center">
                          <h3 className="font-medium text-lg">{prompt.name}</h3>
                        </div>
                        <div className="flex flex-row-reverse gap-2 mr-2">
                          <Button
                            size="icon"
                            className="bg-accent text-accent-foreground"
                            onClick={() => {
                              const personalityId =
                                prompt.personality_id || activePersonalityId;
                              if (!personalityId) {
                                toast.error("No personality selected");
                                return;
                              }
                              dispatch(
                                createThread({
                                  personalityId,
                                  prompt: prompt.text,
                                })
                              )
                                .unwrap()
                                .then(({ thread }) => {
                                  if (prompt.personality_id) {
                                    dispatch(
                                      setActivePersonality(personalityId)
                                    );
                                  }
                                  navigate(`/thread/${thread.id}`);
                                })
                                .catch((error) => {
                                  toast.error("Failed to create thread", {
                                    description:
                                      error?.message ||
                                      "An unexpected error occurred",
                                  });
                                });
                            }}
                          >
                            <CornerDownLeft className="h-4 w-4" />
                          </Button>
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
                </div>
              </div>
            ))}
          {prompts.length === 0 && (
            <div className="p-4 flex justify-center items-center">
              <p className="text-sm text-gray-600">No saved prompts</p>
            </div>
          )}
        </div>
      </ScrollArea>

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
            disabled={isUpdating}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
