import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MediaList } from "@/slices/mediaListsSlice";
import { Share2, PlayCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import MediaItemList from "@/messages/MediaItemList";
import { useGlobalAudio } from "@/contexts/GlobalAudioContext";
import { useAppSelector } from "@/hooks";
import { ScrollArea } from "@/components/ui/scroll-area";

interface MediaListCardProps {
  list: MediaList;
  isSharedView?: boolean;
}

function MediaListCard({ list, isSharedView = false }: MediaListCardProps) {
  const navigate = useNavigate();
  const { clearQueue, playAudio, toggleAutoAdvance, addToQueue } =
    useGlobalAudio();
  const mediaItems = useAppSelector((state) => {
    return state.mediaLists.mediaListItems
      .filter((item) => item.media_list_id === list.id)
      .sort((a, b) => a.index - b.index)
      .map((listItem) =>
        state.media.items.find((item) => item.id === listItem.media_item_id)
      )
      .filter((item): item is NonNullable<typeof item> => item != null);
  });
  const audioItems = mediaItems.filter((item) => item.type === "audio");
  return (
    <Card>
      <CardHeader>
        <CardTitle>{list.name}</CardTitle>
        <CardDescription>{list.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-full">
          <MediaItemList mediaItems={mediaItems} showControls={true} />
        </ScrollArea>
      </CardContent>
      <CardFooter className="flex flex-wrap gap-2">
        <Badge
          className="text-xs capitalize"
          variant={list.visibility === "private" ? "outline" : "default"}
        >
          {list.visibility}
        </Badge>
        <Badge className="text-xs">{mediaItems.length}</Badge>
        {list.shared_with.length > 0 && (
          <Badge variant="secondary">
            Shared with {list.shared_with.length}
          </Badge>
        )}
        <div className="flex-1" />
        {audioItems.length > 0 && (
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => {
              clearQueue();
              // Add all items to queue
              const promises = audioItems.map(
                (item) =>
                  new Promise<void>((resolve) => {
                    addToQueue(item.url, item.name);
                    resolve();
                  })
              );

              // Once all items are added to queue
              Promise.all(promises).then(() => {
                // Enable auto-advance
                toggleAutoAdvance();
                // Play first item
                if (audioItems.length > 0) {
                  playAudio(audioItems[0].url, audioItems[0].name, true);
                }
              });
            }}
          >
            <PlayCircle className="size-4" />
            <span className="sr-only">Play Audio</span>
          </Button>
        )}
        {!isSharedView && (
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => navigate(`/share/${list.id}`)}
          >
            <Share2 className="size-4" />
            Share
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

export default MediaListCard;
