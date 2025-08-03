import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { MediaItem } from "@/types/media";
import { ReactNode } from "react";

type BaseMediaProps = {
  className?: string;
  url: string;
  alt?: string;
  name?: string;
  description?: string;
  width?: number;
  height?: number;
  showControls?: boolean;
  mediaItem?: MediaItem;
  metadata?: Record<string, unknown>;
  triggerClassName?: string;
  dialogTitle?: string;
};

type ImageMediaProps = BaseMediaProps & {
  type: "image";
  thumbnail_size?: "o" | "t" | "l" | "xl" | "xxl";
  display_size?: "o" | "t" | "l" | "xl" | "xxl";
  preload?: boolean;
  objectFit?: "cover" | "contain";
};

type VideoMediaProps = BaseMediaProps & {
  type: "video";
  poster?: string;
  autoplay?: boolean;
  loop?: boolean;
  muted?: boolean;
  controls?: boolean;
};

type AudioMediaProps = BaseMediaProps & {
  type: "audio";
  autoplay?: boolean;
  loop?: boolean;
  controls?: boolean;
  waveform?: string;
};

type SubtitleMediaProps = BaseMediaProps & {
  type: "subtitle";
  content: string;
  language?: string;
};

type SearchResultMediaProps = BaseMediaProps & {
  type: "search_result";
  id: string;
  query?: string;
  score?: number;
};

export type MediaDialogProps = ImageMediaProps | VideoMediaProps | AudioMediaProps | SubtitleMediaProps | SearchResultMediaProps;

interface MediaDialogComponentProps {
  children: ReactNode;
  trigger: ReactNode;
  title: string;
  actions?: ReactNode;
  metadata?: Record<string, unknown>;
  description?: string;
  dimensions?: { width?: number; height?: number };
  className?: string;
}

const MediaDialogComponent: React.FC<MediaDialogComponentProps> = ({
  children,
  trigger,
  title,
  actions,
  metadata,
  description,
  dimensions,
  className,
}) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger}
      </DialogTrigger>
      <DialogContent className={cn("max-w-[95vw] max-h-[95vh] w-full h-[90vh] p-0 overflow-hidden", className)}>
        <div className="grid grid-cols-1 [@media(orientation:landscape)_and_(min-width:768px)]:grid-cols-[1fr,350px] [@media(min-width:1366px)]:grid-cols-[1fr,400px] h-full max-h-full overflow-y-auto">
          {/* Media Section */}
          <div className="relative flex items-center justify-center bg-black/5 dark:bg-white/5 min-h-0">
            {children}
          </div>

          {/* Details Section */}
          <div className="flex flex-col border-t [@media(orientation:landscape)_and_(min-width:768px)]:border-t-0 [@media(orientation:landscape)_and_(min-width:768px)]:border-l [@media(min-width:1366px)]:border-t-0 [@media(min-width:1366px)]:border-l h-full min-h-0 [@media(orientation:landscape)_and_(min-width:768px)]:max-h-[90vh] [@media(min-width:1366px)]:max-h-[90vh]">
            <DialogHeader className="px-6 py-4 border-b shrink-0 text-left">
              <DialogTitle className="text-lg pr-8">{title}</DialogTitle>
            </DialogHeader>

            {/* Action Toolbar */}
            {actions && (
              <div className="flex items-center gap-2 border-b px-6 py-2">
                {actions}
              </div>
            )}

            <div className="flex-1 overflow-y-auto">
              <div className="space-y-4 px-6 py-4">
                {description && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
                    <p className="text-sm whitespace-pre-wrap">{description}</p>
                  </div>
                )}

                {/* Dimensions */}
                {(dimensions?.width || dimensions?.height) && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Dimensions</h3>
                    <p className="text-sm">
                      {dimensions.width && dimensions.height ? `${dimensions.width} × ${dimensions.height}` : dimensions.width ? `Width: ${dimensions.width}` : `Height: ${dimensions.height}`}
                    </p>
                  </div>
                )}

                {/* Metadata */}
                {metadata && Object.keys(metadata).length > 0 && (
                  <>
                    <div className="border-t -mx-6 my-4" />
                    <dl>
                      {Object.entries(metadata)
                        .filter(([, value]) => value !== null && value !== undefined && value !== '')
                        .map(([key, value]) => (
                          <div key={key} className="text-sm mb-4">
                            <dt className="font-medium text-muted-foreground capitalize mb-1">{key.replace(/_/g, ' ')}</dt>
                            <dd className="text-foreground break-words">{String(value)}</dd>
                          </div>
                        ))}
                    </dl>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MediaDialogComponent;
