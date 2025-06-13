import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { AppDispatch } from "../store";
import { fetchPersonalityEmbeddings } from "../actions/personalityActions";
import {
  Embedding,
  selectEmbeddingspersonality,
} from "../slices/embeddingsSlice";
import { RootState } from "../store";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Trash2, Pencil, ArrowUpDown, ArrowLeft } from "lucide-react";
import { withAdminAuth } from "./hoc/withAdminAuth";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  deleteEmbedding,
  bulkDeleteEmbeddings,
  updateEmbedding,
} from "../actions/embeddingsActions";
import { Textarea } from "@/components/ui/textarea";
import { DataTable } from "@/components/DataTable";
import { sortingFns } from "@tanstack/react-table";

interface DeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void>;
  count?: number;
}

import { ColumnDef } from "@tanstack/react-table";

interface EmbeddingMetadata {
  created_at?: number;
  stats?: {
    total?: number;
    useful?: number;
    last_recall_at?: number;
    last_useful_at?: number;
  };
  [key: string]: unknown;
}

const DeleteDialog = ({
  open,
  onOpenChange,
  onConfirm,
  count,
}: DeleteDialogProps) => {
  const handleConfirm = async () => {
    await onConfirm();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Are you absolutely sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete{" "}
            {count ? `${count} embeddings` : "this embedding"} and remove the
            data from our servers.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleConfirm}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

interface EditDialogProps {
  id?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (content: string) => Promise<void>;
  initialContent: string;
}

const EditDialog = ({
  id,
  open,
  onOpenChange,
  onConfirm,
  initialContent,
}: EditDialogProps) => {
  const [content, setContent] = useState(initialContent);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(content);
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (id) {
      setContent(initialContent);
    }
  }, [id, initialContent]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[625px]">
        <DialogHeader>
          <DialogTitle>Edit Embedding</DialogTitle>
        </DialogHeader>
        <div className="py-4">
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="min-h-[200px]"
          />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="mr-2 h-4 w-4" /> : null}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const formatTimestamp = (timestamp: number | undefined) => {
  if (!timestamp) return "Never";
  return new Date(timestamp * 1000).toLocaleString();
};

function EmbeddingsViewComponent() {
  const { personalityId } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const embeddings = useSelector((state: RootState) =>
    selectEmbeddingspersonality(state, personalityId!)
  );
  const isLoading = useSelector((state: RootState) => state.embeddings.loading);
  const [rowSelection, setRowSelection] = useState({});

  const [deleteTarget, setDeleteTarget] = useState<{
    id?: string;
    count?: number;
  } | null>(null);

  const [editTarget, setEditTarget] = useState<{
    id: string;
    content: string;
  } | null>(null);

  useEffect(() => {
    if (personalityId) {
      dispatch(fetchPersonalityEmbeddings(personalityId));
    }
  }, [personalityId, dispatch]);

  const getSelectedIds = () => {
    return Object.keys(rowSelection).map((index) => {
      const row = embeddings[parseInt(index)];
      return row.id;
    });
  };

  const handleDeleteSelected = async () => {
    try {
      const selectedIds = getSelectedIds();
      await dispatch(bulkDeleteEmbeddings(selectedIds));
      setRowSelection({});
      toast("Embeddings deleted", {
        description: `Successfully deleted ${selectedIds.length} embeddings`,
      });
    } catch (error) {
      toast.error("Failed to delete embeddings", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
    setDeleteTarget(null);
  };

  const handleDeleteOne = async (id: string) => {
    try {
      await dispatch(deleteEmbedding(id));
      toast("Embedding deleted");
    } catch (error) {
      toast.error("Failed to delete embedding", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
    setDeleteTarget(null);
  };

  const handleEdit = async (id: string, content: string) => {
    try {
      await dispatch(updateEmbedding({ id, content })).unwrap();

      // Refresh the embeddings list
      if (personalityId) {
        dispatch(fetchPersonalityEmbeddings(personalityId));
      }

      toast("Embedding updated", {
        description: "The embedding has been successfully updated",
      });
    } catch (error) {
      toast.error("Failed to update embedding", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
  };

  const columns: ColumnDef<Embedding>[] = [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected()}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: "collection_name",
      header: "Collection",
    },
    {
      accessorKey: "document",
      header: "Document",
    },
    {
      id: "total_recalls",
      accessorFn: (row) => row.cmetadata?.stats?.total || 0,
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Total Recalls
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ getValue }) => (
        <div className="text-right">{getValue() as number}</div>
      ),
      sortingFn: sortingFns.alphanumeric,
      enableSorting: true,
    },
    {
      id: "useful_recalls",
      accessorFn: (row) => row.cmetadata?.stats?.useful || 0,
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Useful Recalls
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ getValue }) => (
        <div className="text-right">{getValue() as number}</div>
      ),
      sortingFn: sortingFns.alphanumeric,
      enableSorting: true,
    },
    {
      id: "last_recall_at",
      accessorFn: (row) => row.cmetadata?.stats?.last_recall_at || 0,
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Last Recalled
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ getValue }) => (
        <div className="text-right whitespace-nowrap">
          {formatTimestamp(getValue() as number)}
        </div>
      ),
      sortingFn: sortingFns.alphanumeric,
      enableSorting: true,
    },
    {
      id: "last_useful_at",
      accessorFn: (row) => row.cmetadata?.stats?.last_useful_at || 0,
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Last Useful
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ getValue }) => (
        <div className="text-right whitespace-nowrap">
          {formatTimestamp(getValue() as number)}
        </div>
      ),
      sortingFn: sortingFns.alphanumeric,
      enableSorting: true,
    },
    {
      id: "created_at",
      accessorFn: (row) => row.cmetadata?.created_at || 0,
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Created At
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ getValue }) => {
        const timestamp = getValue() as number;
        return (
          <div className="text-right whitespace-nowrap">
            {timestamp ? new Date(timestamp * 1000).toLocaleString() : "N/A"}
          </div>
        );
      },
      sortingFn: sortingFns.alphanumeric,
      enableSorting: true,
    },
    {
      accessorFn: (row) => row.cmetadata,
      header: "Metadata",
      cell: ({ getValue }) => {
        const metadata = getValue() as EmbeddingMetadata;
        return Object.entries(metadata)
          .filter(([key]) => !["created_at", "stats"].includes(key))
          .map(([key, value]) => (
            <div key={key} className="text-sm">
              <span className="font-medium">{key}:</span>{" "}
              {JSON.stringify(value)}
            </div>
          ));
      },
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() =>
              setEditTarget({
                id: row.original.id,
                content: row.original.document,
              })
            }
            className="text-muted-foreground hover:text-foreground"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setDeleteTarget({ id: row.original.id })}
            className="text-destructive hover:text-destructive/90"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  if (isLoading && embeddings.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen">
      <div className="flex justify-between mb-2 border-b pb-2 sticky top-0 bg-background z-10">
        <Button
          className="mr-4"
          variant="ghost"
          size="icon"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="size-4" />
        </Button>
        <h1 className="text-2xl font-bold">
          Personality Embeddings{" "}
          <span className="text-sm text-muted-foreground ml-2">
            ({embeddings.length} total)
          </span>
        </h1>
        <div className="flex-1" />
      </div>

      <DeleteDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        onConfirm={() =>
          deleteTarget?.id
            ? handleDeleteOne(deleteTarget.id)
            : handleDeleteSelected()
        }
        count={deleteTarget?.count}
      />
      <EditDialog
        id={editTarget?.id}
        open={editTarget !== null}
        onOpenChange={(open) => {
          if (!open) setEditTarget(null);
        }}
        onConfirm={(content) =>
          editTarget ? handleEdit(editTarget.id, content) : Promise.resolve()
        }
        initialContent={editTarget?.content || ""}
      />

      {Object.keys(rowSelection).length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4 shadow-lg z-50">
          <div className="container mx-auto flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {Object.keys(rowSelection).length} item(s) selected
            </span>
            <Button
              variant="destructive"
              onClick={() =>
                setDeleteTarget({ count: Object.keys(rowSelection).length })
              }
              className="flex items-center gap-2"
            >
              <Trash2 className="h-4 w-4" />
              Delete Selected
            </Button>
          </div>
        </div>
      )}
      <DataTable
        columns={columns}
        data={embeddings}
        onRowSelectionChange={setRowSelection}
        state={{ rowSelection }}
        initialSorting={[{ id: "created_at", desc: true }]}
      />
    </div>
  );
}

export const EmbeddingsView = withAdminAuth(EmbeddingsViewComponent, true);
