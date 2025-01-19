import { ComponentType } from "react";
import { useAppSelector } from "@/hooks";
import { MediaList } from "@/slices/mediaListsSlice";
import { MediaListItem } from "@/slices/mediaListsSlice";
// Define the props that will be injected by the HOC
interface WithMediaItemsProps {
  mediaListItems: MediaListItem[];
}

// Define the props that the wrapped component needs
interface WrappedComponentProps {
  list: MediaList;
}

export function withMediaItems<P extends WithMediaItemsProps>(
  WrappedComponent: ComponentType<P>
) {
  return function WithMediaItemsComponent(
    props: Omit<P, keyof WithMediaItemsProps> & WrappedComponentProps
  ) {
    const mediaListItems = useAppSelector((state) => {
      return state.mediaLists.mediaListItems
        .filter((item) => item.media_list_id === props.list.id)
        .sort((a, b) => a.index - b.index);
    });
    // Create a new props object with both the original props and mediaItems
    const combinedProps = {
      ...props,
      mediaListItems,
    } as unknown as P;

    return <WrappedComponent {...combinedProps} />;
  };
}
