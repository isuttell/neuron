import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, Copy } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";

interface VideoContentProps {
  url: string;
  autoPlay?: boolean;
  muted?: boolean;
  controls?: boolean;
  loop?: boolean;
}

const VideoContent: React.FC<VideoContentProps> = ({
  url,
  autoPlay = false,
  muted = false,
  controls = false,
  loop = false,
}) => {
  const { toast } = useToast();
  return (
    <Dialog>
      <DialogTrigger>
        <div className="relative">
          <video
            className="rounded-md border border-gray-900 w-full"
            src={url}
            autoPlay={autoPlay}
            muted={muted}
            controls={controls}
            loop={loop}
          />
          <div className="absolute bottom-2 right-2 space-x-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  className=""
                  variant="outline"
                  onClick={(e) => {
                    e.preventDefault();
                    navigator.clipboard.writeText(url);
                    toast({
                      title: "Video URL copied to clipboard",
                    });
                  }}
                >
                  <Copy />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Copy video URL</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  asChild
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                >
                  <a
                    className="text-primary"
                    href={url}
                    download
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Download />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Download image</TooltipContent>
            </Tooltip>
          </div>
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <DialogHeader>
          <DialogTitle>Video</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-hidden">
          <video
            className="w-full h-full rounded-md object-contain bg-black"
            autoPlay={true}
            controls={true}
            loop={true}
            playsInline
            muted={false}
          >
            <source src={url} type="video/mp4" />
          </video>
        </div>
        <Button className="w-full" variant="outline" asChild>
          <a
            className="text-primary"
            href={url}
            download
            target="_blank"
            rel="noopener noreferrer"
          >
            <Download className="w-4 h-4" />
            Download
          </a>
        </Button>
      </DialogContent>
    </Dialog>
  );
};

export default VideoContent;
