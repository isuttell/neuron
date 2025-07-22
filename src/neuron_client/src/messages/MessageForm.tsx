import { AttachmentIndicator } from "@/components/AttachmentIndicator";
import { AudioRecorder } from "@/components/AudioRecorder";
import { PromptDropdown } from "@/components/PromptDropdown";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { CornerDownLeft, Upload, X, Check } from "lucide-react";
import { useState, useRef, useEffect, ReactNode } from "react";

/**
 * Props for the MessageForm component - a pure presentation component for message input
 */
interface MessageFormProps {
  /** Whether the form should be disabled (prevents all interactions) */
  disabled?: boolean;
  /** Whether the form is in a loading state (shows spinner, disables submit) */
  isLoading?: boolean;
  /** Placeholder text for the textarea input */
  placeholder?: string;
  /** Additional CSS classes to apply to the form element */
  className?: string;
  /** Whether to show the upload button (default: true) */
  showUpload?: boolean;
  /** Whether to show the record button (default: true) */
  showRecord?: boolean;
  /** Whether to show the prompts dropdown (default: true) */
  showPrompts?: boolean;
  /** Initial value for the textarea (used when editing messages) */
  initialValue?: string;
  /** Whether the form is in edit mode */
  editMode?: boolean;
  /**
   * Callback fired when the form is submitted
   * @param value - The trimmed text content of the message
   * @param file - Optional file attachment (File object or Blob for recordings)
   */
  onSubmit: (value: string, file?: File | Blob) => void;
  /**
   * Callback fired when a file is added (upload or recording)
   * @param file - The file or audio blob that was added
   * @param isRecording - True if this is an audio recording, false for file upload
   */
  onFileAdd?: (file: File | Blob, isRecording: boolean) => void;
  /**
   * Callback fired when a file attachment is removed
   */
  onFileRemove?: () => void;
  /**
   * Callback fired when the cancel button is clicked (during loading state or edit mode)
   */
  onCancel?: () => void;
  /**
   * Callback fired when editing is cancelled
   */
  onCancelEdit?: () => void;

  /**
   * Optional children to render to the left of the buttons
   */
  children?: ReactNode
}

/**
 * MessageForm - A pure presentation component for message input with file attachments
 *
 * This component provides a rich text input form with support for:
 * - Text message input with keyboard shortcuts (Enter to submit, Shift+Enter for newlines)
 * - File upload with drag & drop support
 * - Audio recording with auto-send functionality
 * - Visual feedback for loading and disabled states
 * - Attachment indicators and removal
 * - Prompt suggestions dropdown
 *
 * The component is designed to be reusable across different contexts by using
 * callback props for all business logic operations.
 *
 * @example
 * ```tsx
 * <MessageForm
 *   onSubmit={(text, file) => console.log('Submitted:', text, file)}
 *   onFileAdd={(file, isRecording) => showToast('File added')}
 *   onFileRemove={() => showToast('File removed')}
 *   placeholder="Type your message..."
 *   isLoading={false}
 *   disabled={false}
 * />
 * ```
 */
export default function MessageForm({
  disabled = false,
  isLoading = false,
  placeholder = "Type your message here...",
  className = "",
  showUpload = true,
  showRecord = true,
  showPrompts = true,
  initialValue = "",
  editMode = false,
  onSubmit,
  onFileAdd,
  onFileRemove,
  onCancel,
  onCancelEdit,
  children = undefined,
}: MessageFormProps) {
  const [value, setValue] = useState(initialValue);
  const [file, setFile] = useState<File | Blob | undefined>(undefined);
  const [isAudioRecording, setIsAudioRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Update value when initialValue changes (for edit mode)
  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  useEffect(() => {
    // Focus textarea when thread becomes idle
    if (!isLoading) {
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  }, [isLoading]);

  /**
   * Handles form submission with validation and cleanup
   *
   * @param e - Optional form event (prevented if provided)
   */
  const handleSubmit = (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }

    if ((!value.trim().length && !file) || isLoading) {
      return;
    }

    onSubmit(value.trim(), file);
    setValue("");
    setFile(undefined);
    setIsAudioRecording(false);
  };

  /**
   * Handles file selection from the file input
   *
   * @param e - File input change event
   */
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFile(file);
      setIsAudioRecording(false);
      onFileAdd?.(file, false);
    }
  };

  const isDisabled = disabled || isLoading;
  const isSubmitDisabled = !value.trim().length && !file;

  return (
    <form className={className} onSubmit={handleSubmit}>
      <Label htmlFor="message" className="sr-only">
        Message
      </Label>
      <div className="space-y-2">
        <Textarea
          ref={textareaRef}
          id="message"
          placeholder={placeholder}
          className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4"
          value={value}
          disabled={isDisabled}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            } else if (e.key === "Escape" && editMode) {
              e.preventDefault();
              onCancelEdit?.();
            }
          }}
        />
        {file && (
          <AttachmentIndicator
            type={isAudioRecording ? "audio" : "file"}
            name={file instanceof File ? file.name : undefined}
            onRemove={() => {
              setFile(undefined);
              setIsAudioRecording(false);
              onFileRemove?.();
            }}
          />
        )}
      </div>
      <div className="flex flex-row flex-nowrap items-center gap-2 pt-2">
        {children && <div>
          {children}
        </div>}
        <div className="flex-1" />
        {showUpload && (
          <Button
            type="button"
            size="sm"
            variant={file ? "default" : "outline"}
            className="size-10 gap-1.5 flex-shrink-0"
            disabled={isDisabled}
            onClick={() => {
              if (file) {
                setFile(undefined);
                setIsAudioRecording(false);
                onFileRemove?.();
              } else {
                document.getElementById("file-upload")?.click();
              }
            }}
          >
            <Upload className="size-3.5" />
          </Button>
        )}
        {showRecord && (
          <AudioRecorder
            className="size-10 flex-shrink-0"
            disabled={isDisabled || !!file}
            onRecordingComplete={(blob) => {
              setFile(blob);
              setIsAudioRecording(true);
              onFileAdd?.(blob, true);
            }}
            onAutoSend={(blob) => {
              onSubmit(value, blob);
              setValue("");
              setFile(undefined);
              setIsAudioRecording(false);
            }}
          />
        )}
        {showPrompts && (
          <PromptDropdown
            disabled={isDisabled}
            onSelectPrompt={(promptText) => setValue(promptText)}
          />
        )}
        {showUpload && (
          <input
            id="file-upload"
            type="file"
            className="hidden"
            onChange={handleFileUpload}
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.md,.txt,.csv,.srt,.vtt,.mp3,.wav,.mp4,.heic,.heif"
          />
        )}
        {/* Cancel button for edit mode */}
        {editMode && !isLoading && (
          <Button
            onClick={() => onCancelEdit?.()}
            type="button"
            size="sm"
            variant="outline"
            data-testid="cancel-edit-button"
            className="size-10 flex-shrink-0"
          >
            <X className="size-3.5" />
          </Button>
        )}

        {/* Submit/Update button */}
        <Button
          onClick={() => isLoading ? onCancel?.() : handleSubmit()}
          type={isLoading ? "button" : "submit"}
          size="sm"
          data-testid={isLoading ? "cancel-button" : editMode ? "update-button" : "submit-button"}
          disabled={!isLoading && (isSubmitDisabled || isDisabled)}
          className={cn(
            "size-10 flex-shrink-0",
            isLoading
              ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
              : isSubmitDisabled || isDisabled
              ? "bg-muted text-muted-foreground cursor-not-allowed"
              : "bg-accent text-accent-foreground"
          )}
        >
          {isLoading ? (
            <X className="size-3.5" />
          ) : editMode ? (
            <Check className="size-3.5" />
          ) : (
            <CornerDownLeft className="size-3.5" />
          )}
        </Button>
      </div>
    </form>
  );
}
