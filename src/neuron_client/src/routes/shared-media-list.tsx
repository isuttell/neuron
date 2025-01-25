import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import { Button } from "@/components/ui/button";
import { useAppDispatch, useAppSelector } from "@/hooks";
import {
  fetchMediaList,
  selectMediaListsLoading,
  selectMediaListsError,
} from "@/slices/mediaListsSlice";
import MediaListCard from "@/components/MediaListCard";
import Loading from "@/lib/loading";

export default function SharedMediaList() {
  const { listId } = useParams();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const loading = useAppSelector(selectMediaListsLoading);
  const error = useAppSelector(selectMediaListsError);
  const list = useAppSelector((state) =>
    state.mediaLists.lists.find((l) => l.id === listId)
  );

  useEffect(() => {
    if (listId) {
      dispatch(fetchMediaList(listId));
    }
  }, [dispatch, listId]);

  if (error) {
    return (
      <div className="container py-6">
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  if (loading) {
    return <Loading />;
  }

  if (!list) {
    return (
      <div className="container py-6">
        <div className="text-red-500">Media list not found</div>
      </div>
    );
  }

  return (
    <MediaPlayerProvider>
      <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
        <div className="flex justify-between mb-2 border-b pb-2">
          <Button
            className="mr-4"
            variant="ghost"
            size="icon"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="size-4" />
          </Button>
          <div className="flex-1" />
        </div>
        <div className="max-w-3xl mx-auto w-full">
          <MediaListCard list={list} isSharedView />
        </div>
      </div>
    </MediaPlayerProvider>
  );
}
