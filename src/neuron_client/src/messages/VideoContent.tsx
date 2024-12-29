import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
  return (
    <Dialog>
      <DialogTrigger>
        <video
          className="rounded-md border border-gray-900"
          src={url}
          autoPlay={autoPlay}
          muted={muted}
          controls={controls}
          loop={loop}
        />
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <DialogHeader>
          <DialogTitle>Video</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-hidden">
          <video
            className="w-full rounded-md max-h-full"
            autoPlay={true}
            controls={true}
            loop={true}
            playsInline
            muted={false}
          >
            <source src={url} type="video/mp4" />
          </video>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default VideoContent;
