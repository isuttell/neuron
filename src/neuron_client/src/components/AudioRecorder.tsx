import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Mic, Square } from "lucide-react";
import { useToast } from "../hooks/use-toast";

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  onAutoSend?: (blob: Blob) => void;
  disabled?: boolean;
  className?: string;
}

export function AudioRecorder({
  onRecordingComplete,
  onAutoSend,
  disabled = false,
  className,
}: AudioRecorderProps) {
  const { toast } = useToast();
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      chunks.current = [];

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.current.push(e.data);
        }
      };

      mediaRecorder.current.onstop = () => {
        const blob = new Blob(chunks.current, { type: "audio/webm" });
        onRecordingComplete(blob);

        // Auto send if handler provided
        if (onAutoSend) {
          onAutoSend(blob);
        }

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      toast({
        variant: "destructive",
        title: "Microphone Error",
        description:
          "Failed to access microphone. Please ensure you have granted permission.",
      });
    }
  };

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  return (
    <Button
      type="button"
      size="sm"
      className={className}
      variant={isRecording ? "destructive" : "outline"}
      disabled={disabled}
      onClick={isRecording ? stopRecording : startRecording}
    >
      {isRecording ? (
        <Square className="size-3.5" />
      ) : (
        <Mic className="size-3.5" />
      )}
    </Button>
  );
}
