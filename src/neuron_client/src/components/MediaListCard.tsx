import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MediaList } from "@/slices/mediaListsSlice";
import MediaItemList from "@/messages/MediaItemList";
import { useAppSelector } from "@/hooks";
import { ScrollArea } from "@/components/ui/scroll-area";

interface MediaListCardProps {
  list: MediaList;
}

function MediaListCard({ list }: MediaListCardProps) {
  const mediaItems = useAppSelector((state) => {
    const mediaListItems = state.mediaLists.mediaListItems
      .filter((item) => item.media_list_id === list.id)
      .sort((a, b) => a.index - b.index);
    return state.media.items.filter((item) =>
      mediaListItems.some((listItem) => listItem.media_item_id === item.id)
    );
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle>{list.name}</CardTitle>
        <CardDescription>{list.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-full">
          <MediaItemList mediaItems={mediaItems} />
        </ScrollArea>
      </CardContent>
      <CardFooter className="flex justify-between">
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
      </CardFooter>
    </Card>
  );
}

export default MediaListCard;
