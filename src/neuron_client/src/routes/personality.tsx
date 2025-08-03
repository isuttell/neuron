import { useEffect, useState, useRef } from "react";
import { Trash, ArrowLeft, Upload } from "lucide-react";
import { useParams, useNavigate } from "react-router-dom";
import { useAppSelector, useAppDispatch } from "../hooks";
import { CornerDownLeft } from "lucide-react";
import { shallowEqual } from "react-redux";
import { RootState } from "../store";
import { Button } from "@/components/ui/button";
import Loading from "@/lib/loading";
import { getPersonalityDocuments } from "../slices/personalitiesSlice";
import type { PersonalityDocument } from "../slices/personalitiesSlice.d";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import { addPersonalityDocuments } from "../slices/personalitiesSlice";
import {
  fetchPersonality,
  updatePersonality,
  deletePersonality,
  fetchPersonalityDocuments,
  deletePersonalityDocument,
} from "../actions/personalityActions";
import EditPersonalityDialog from "../personalities/EditPersonalityDialog";
import PersonalityUsersDialog from "../personalities/PersonalityUsersDialog";
import { toast } from "sonner";
import { api } from "@/lib/api";
import ToolsetSelector from "../components/ToolsetSelector";
import { Card } from "@/components/ui/card";

const selectPersonality = (state: RootState, personalityId?: string) =>
  state.personalities.personalities.find((per) => per.id === personalityId);

export default function Personality() {
  const [updatedContext, setUpdatedContext] = useState("");
  const [updatedName, setUpdatedName] = useState("");
  const [updatedToolSet, setUpdatedToolSet] = useState<string[]>([]);
  const [prompt, setPrompt] = useState("");
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { personalityId } = useParams();
  const personality = useAppSelector(
    (state) => selectPersonality(state, personalityId),
    shallowEqual
  );
  const documents = useAppSelector((state) =>
    personalityId ? getPersonalityDocuments(state, personalityId) : []
  );

  useEffect(() => {
    if (!personalityId) {
      return;
    }
    dispatch(fetchPersonality(personalityId));
    dispatch(fetchPersonalityDocuments(personalityId));
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !personality?.id) return;

    // Validate file types
    const validTypes = ['.txt', '.md', '.markdown'];
    const invalidFiles: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileExtension = file.name.substring(file.name.lastIndexOf('.'));
      if (!validTypes.includes(fileExtension)) {
        invalidFiles.push(file.name);
      }
    }

    if (invalidFiles.length > 0) {
      toast.error(`Invalid file type(s): ${invalidFiles.join(', ')}. Only .txt, .md, and .markdown files are allowed.`);
      return;
    }

    setIsUploadingDocument(true);
    try {
      // Create FormData with files
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append(`file${i}`, files[i]);
      }

      // Call API directly to avoid Redux serialization issues with File objects
      const response = await api.post<{ personality_documents: PersonalityDocument[] }>(
        `/personalities/${personality.id}/documents`,
        formData
      );

      // Dispatch the simple action with the response
      dispatch(addPersonalityDocuments({
        personalityId: personality.id,
        documents: response.personality_documents
      }));

      const message = files.length === 1
        ? `Document "${files[0].name}" uploaded successfully`
        : `${files.length} documents uploaded successfully`;
      toast.success(message);
    } catch {
      toast.error("Failed to upload documents");
    } finally {
      setIsUploadingDocument(false);
      // Reset the input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteDocument = async (documentId: string, documentName: string) => {
    if (!personality?.id) return;

    try {
      await dispatch(deletePersonalityDocument({
        personalityId: personality.id,
        documentId
      })).unwrap();
      toast.success(`Document "${documentName}" deleted`);
    } catch {
      toast.error("Failed to delete document");
    }
  };

  if (!personality) {
    return <Loading />;
  }


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
        </h1>
        <div className="flex-1" />
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.markdown"
          onChange={handleFileUpload}
          className="hidden"
          multiple
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploadingDocument}
        >
          {isUploadingDocument ? (
            <Spinner className="size-4" />
          ) : (
            <Upload className="size-4" />
          )}
          <span className="sr-only">Upload Document</span>
        </Button>
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

          {/* Documents Section */}
          {documents.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 mb-4">
              {documents.map((doc) => (
                  <Card key={doc.id} className="p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm truncate flex-1">{doc.name}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 ml-2 flex-shrink-0"
                        onClick={() => handleDeleteDocument(doc.id, doc.name)}
                      >
                        <Trash className="size-3.5" />
                        <span className="sr-only">Delete document</span>
                      </Button>
                    </div>
                  </Card>
                ))}
            </div>
          )}

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
