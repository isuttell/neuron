import { useState, useRef, useCallback, useEffect } from "react";
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
  const [isPushToTalk, setIsPushToTalk] = useState(false);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stream = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      mediaRecorder.current = new MediaRecorder(stream.current);
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
        stream.current?.getTracks().forEach((track) => track.stop());
        stream.current = null;
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
  }, [onAutoSend, onRecordingComplete, toast]);

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  // Handle keyboard shortcuts for push-to-talk
  useEffect(() => {
    if (disabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Check for Ctrl+Shift+. (push-to-talk)
      if (e.ctrlKey && e.shiftKey && e.key === ".") {
        e.preventDefault();
        if (!isPushToTalk && !isRecording) {
          setIsPushToTalk(true);
          startRecording();
        }
      }
      // Check for Ctrl+Shift+/ (toggle recording)
      else if (e.ctrlKey && e.shiftKey && e.key === "?") {
        e.preventDefault();
        if (isRecording) {
          stopRecording();
        } else {
          startRecording();
        }
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      // Only handle key up for push-to-talk (Ctrl+Shift+.)
      if (
        isPushToTalk &&
        (e.key === "Control" || e.key === "Shift" || e.key === ".")
      ) {
        setIsPushToTalk(false);
        stopRecording();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);

      // Cleanup recording if component unmounts while recording
      if (isRecording) {
        stopRecording();
        stream.current?.getTracks().forEach((track) => track.stop());
        stream.current = null;
      }
    };
  }, [disabled, isPushToTalk, isRecording, startRecording, stopRecording]);

  return (
    <Button
      type="button"
      size="sm"
      className={className}
      variant={
        isRecording ? (isPushToTalk ? "default" : "destructive") : "outline"
      }
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
