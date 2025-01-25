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
import { Share2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import MediaItemList from "@/messages/MediaItemList";
import { useAppSelector } from "@/hooks";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MediaListAudioPlayer } from "./MediaListAudioPlayer";

interface MediaListCardProps {
  list: MediaList;
  isSharedView?: boolean;
}

function MediaListCard({ list, isSharedView = false }: MediaListCardProps) {
  const navigate = useNavigate();
  const mediaItems = useAppSelector((state) => {
    return state.mediaLists.mediaListItems
      .filter((item) => item.media_list_id === list.id)
      .sort((a, b) => a.index - b.index)
      .map((listItem) =>
        state.media.items.find((item) => item.id === listItem.media_item_id)
      )
      .filter((item): item is NonNullable<typeof item> => item != null);
  });
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
      <MediaListAudioPlayer mediaItems={mediaItems} />
    </Card>
  );
}

export default MediaListCard;
