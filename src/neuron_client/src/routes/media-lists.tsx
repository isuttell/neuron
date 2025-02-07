import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/hooks";
import {
  fetchMediaLists,
  selectAllMediaLists,
  selectMediaListsLoading,
  selectMediaListsError,
} from "@/slices/mediaListsSlice";
import NewMediaListDialog from "@/media/NewMediaListDialog";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import { SidebarTrigger } from "@/components/ui/sidebar";
import MediaListCard from "@/components/MediaListCard";
import Loading from "@/lib/loading";

export default function MediaLists() {
  const dispatch = useAppDispatch();
  const lists = useAppSelector(selectAllMediaLists);
  const loading = useAppSelector(selectMediaListsLoading);
  const error = useAppSelector(selectMediaListsError);

  useEffect(() => {
    setTimeout(() => {
      dispatch(fetchMediaLists());
    }, 0);
  }, [dispatch]);

  if (error) {
    return <div className="container py-6 text-red-500">{error}</div>;
  }

  if (loading && lists.length === 0) {
    return <Loading />;
  }

  return (
    <MediaPlayerProvider>
      <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
        <div className="flex justify-between mb-2 border-b pb-2">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-2xl font-bold">Media Lists</h1>
          <div className="flex-1" />
          <NewMediaListDialog />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {lists.map((list) => (
            <MediaListCard key={list.id} list={list} />
          ))}
        </div>
      </div>
    </MediaPlayerProvider>
  );
}
