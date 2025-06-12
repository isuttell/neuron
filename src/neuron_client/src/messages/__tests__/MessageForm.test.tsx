import { vi } from 'vitest';
import type { ToastProps } from "@/components/ui/toast";
import { MessageResponse } from "@/types/message";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Mock } from "jest-mock";
import { useParams } from "react-router-dom";
import { postMessageByThread } from "../../actions/messageActions";
import { useAppDispatch } from "../../hooks";
import { useToast } from "../../hooks/use-toast";
import { AppDispatch } from "../../store";
import MessageForm from "../MessageForm";

type ToastReturnType = {
  id: string;
  dismiss: () => void;
  update: (props: ToastProps) => void;
};

// Mock dependencies
vi.mock("../../hooks", () => ({
  useAppDispatch: vi.fn() as Mock<() => AppDispatch>,
}));

vi.mock("react-router-dom", () => ({
  useParams: vi.fn() as Mock<() => { threadId: string }>,
}));

vi.mock("../../hooks/use-toast", () => ({
  useToast: vi.fn() as Mock<
    () => {
      toast: (props: ToastProps) => ToastReturnType;
      dismiss: (toastId?: string) => void;
      toasts: ToastProps[];
    }
  >,
}));

vi.mock("../../actions/messageActions", () => ({
  postMessageByThread: vi.fn(),
}));

const mockAudioRecorderProps = {
  onRecordingComplete: vi.fn(),
  onAutoSend: vi.fn(),
};

vi.mock("@/components/AudioRecorder", () => ({
  AudioRecorder: (props: typeof mockAudioRecorderProps) => {
    mockAudioRecorderProps.onRecordingComplete = props.onRecordingComplete;
    mockAudioRecorderProps.onAutoSend = props.onAutoSend;
    return <div data-testid="audio-recorder">Audio Recorder</div>;
  },
}));

const mockPromptDropdownProps = {
  onSelectPrompt: vi.fn(),
  disabled: false,
};

vi.mock("@/components/PromptDropdown", () => ({
  PromptDropdown: (props: typeof mockPromptDropdownProps) => {
    mockPromptDropdownProps.onSelectPrompt = props.onSelectPrompt;
    mockPromptDropdownProps.disabled = props.disabled;
    return <div data-testid="prompt-dropdown">Prompt Dropdown</div>;
  },
}));

describe("MessageForm", () => {
  const mockDispatch = vi.fn();
  const mockToast = vi.fn();
  const mockOnSubmit = vi.fn();
  const mockThreadId = "123";
  const mockThread = {
    id: mockThreadId,
    name: "Test Thread",
    context: "Test context",
    memory: "Test memory",
    personality_id: "456",
    status: "idle" as const,
    message_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (
      useAppDispatch as vi.MockedFunction<typeof useAppDispatch>
    ).mockReturnValue(mockDispatch);
    (useParams as vi.MockedFunction<typeof useParams>).mockReturnValue({
      threadId: mockThreadId,
    });
    (useToast as vi.MockedFunction<typeof useToast>).mockReturnValue({
      toast: mockToast,
      dismiss: vi.fn(),
      toasts: [],
    });
    mockDispatch.mockResolvedValue({
      messages: [],
      media: [],
    } as MessageResponse);
  });

  it("renders form elements correctly", () => {
    render(<MessageForm thread={mockThread} />);

    expect(
      screen.getByPlaceholderText("Type your message here...")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    expect(screen.getByTestId("audio-recorder")).toBeInTheDocument();
    expect(screen.getByTestId("prompt-dropdown")).toBeInTheDocument();
  });

  it("handles text input correctly", async () => {
    render(<MessageForm thread={mockThread} onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message");

    expect(input).toHaveValue("Test message");
  });

  it("handles form submission with text", async () => {
    render(<MessageForm thread={mockThread} onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    const submitButton = screen.getByRole("button", { name: /send/i });

    await userEvent.type(input, "Test message");
    fireEvent.click(submitButton);

    expect(mockDispatch).toHaveBeenCalledWith(
      postMessageByThread({
        threadId: mockThreadId,
        prompt: "Test message",
        personalityId: mockThread.personality_id,
        file: undefined,
      })
    );
    expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
    expect(input).toHaveValue("");
  });

  it("prevents submission with empty message and no file", async () => {
    render(<MessageForm thread={mockThread} onSubmit={mockOnSubmit} />);

    const submitButton = screen.getByRole("button", { name: /send/i });
    fireEvent.click(submitButton);

    expect(mockDispatch).not.toHaveBeenCalled();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("handles file upload correctly", async () => {
    render(<MessageForm thread={mockThread} />);

    const file = new File(["test"], "test.txt", { type: "text/plain" });
    const input = document.getElementById("file-upload") as HTMLInputElement;
    await userEvent.upload(input, file);

    const attachmentIndicator = screen.getByText(/file attached: test\.txt/i);
    expect(attachmentIndicator).toBeInTheDocument();
    expect(mockToast).toHaveBeenCalledWith({
      title: "Attachment added",
      description: "test.txt has been added to the message",
    });
  });

  it("handles empty file selection", async () => {
    render(<MessageForm thread={mockThread} />);

    const input = document.getElementById("file-upload") as HTMLInputElement;
    const event = {
      target: { files: null },
    } as unknown as React.ChangeEvent<HTMLInputElement>;
    fireEvent.change(input, event);

    expect(screen.queryByText(/file attached:/i)).not.toBeInTheDocument();
    expect(mockToast).not.toHaveBeenCalled();
  });

  it("handles file removal", async () => {
    render(<MessageForm thread={mockThread} />);

    const file = new File(["test"], "test.txt", { type: "text/plain" });
    const fileInput = document.getElementById(
      "file-upload"
    ) as HTMLInputElement;
    await userEvent.upload(fileInput, file);

    const removeButton = screen.getByLabelText("Remove attachment");
    fireEvent.click(removeButton);

    expect(screen.queryByText(/file attached:/i)).not.toBeInTheDocument();
    expect(mockToast).toHaveBeenCalledWith({
      title: "Attachment removed",
    });
  });

  it("handles Enter key submission", async () => {
    render(<MessageForm thread={mockThread} onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message{enter}");

    expect(mockDispatch).toHaveBeenCalledWith(
      postMessageByThread({
        threadId: mockThreadId,
        prompt: "Test message",
        personalityId: mockThread.personality_id,
        file: undefined,
      })
    );
    expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
  });

  it("shows loading state when thread status is not idle", () => {
    const loadingThread = { ...mockThread, status: "processing" as const };
    render(<MessageForm thread={loadingThread} />);

    const submitButton = screen.getByTestId("submit-button");
    expect(submitButton.querySelector("svg")).toHaveClass("animate-spin");
    expect(screen.queryByText(/send/i)).not.toBeInTheDocument();
  });

  it("handles submission error correctly", async () => {
    const error = new Error("Network error");
    mockDispatch.mockRejectedValueOnce(error);

    render(<MessageForm thread={mockThread} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message");
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        variant: "destructive",
        title: "Failed to send message",
        description: "Network error",
      });
    });
  });

  it("respects disabled prop", () => {
    render(<MessageForm thread={mockThread} disabled={true} />);

    expect(
      screen.getByPlaceholderText("Type your message here...")
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("applies custom className", () => {
    render(<MessageForm thread={mockThread} className="custom-class" />);

    expect(document.querySelector("form")).toHaveClass("custom-class");
  });

  it("prevents submission when threadId is missing", async () => {
    (useParams as vi.Mock).mockReturnValue({ threadId: undefined });
    render(<MessageForm thread={mockThread} onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test message");
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(mockDispatch).not.toHaveBeenCalled();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("handles audio recording completion", async () => {
    render(<MessageForm thread={mockThread} />);

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onRecordingComplete(blob);
    });

    const attachmentIndicator = screen.getByText(/audio recording attached/i);
    expect(attachmentIndicator).toBeInTheDocument();
    expect(mockToast).toHaveBeenCalledWith({
      title: "Recording sent",
      description: "Message added to conversation",
    });
  });

  it("handles auto-send of audio recording", async () => {
    render(<MessageForm thread={mockThread} />);

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onAutoSend(blob);
    });

    expect(mockDispatch).toHaveBeenCalledWith(
      postMessageByThread({
        threadId: mockThreadId,
        prompt: "",
        personalityId: mockThread.personality_id,
        file: blob,
      })
    );
  });

  it("handles auto-send error", async () => {
    const error = new Error("Network error");
    mockDispatch.mockRejectedValueOnce(error);
    render(<MessageForm thread={mockThread} />);

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onAutoSend(blob);
    });

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        variant: "destructive",
        title: "Failed to send message",
        description: "Network error",
      });
    });
  });

  it("prevents auto-send when threadId is missing", async () => {
    (useParams as vi.Mock).mockReturnValue({ threadId: undefined });
    render(<MessageForm thread={mockThread} />);

    const blob = new Blob(["test"], { type: "audio/wav" });
    await act(async () => {
      mockAudioRecorderProps.onAutoSend(blob);
    });

    expect(mockDispatch).not.toHaveBeenCalled();
  });

  it("allows shift+enter for newlines", async () => {
    render(<MessageForm thread={mockThread} onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Type your message here...");
    await userEvent.type(input, "Test{Shift>}{Enter}{/Shift}message");

    expect(input).toHaveValue("Test\nmessage");
    expect(mockDispatch).not.toHaveBeenCalled();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("handles prompt selection", async () => {
    render(<MessageForm thread={mockThread} />);

    await act(async () => {
      mockPromptDropdownProps.onSelectPrompt("Selected prompt");
    });

    const input = screen.getByPlaceholderText("Type your message here...");
    expect(input).toHaveValue("Selected prompt");
  });

  it("disables prompt dropdown when form is disabled", () => {
    render(<MessageForm thread={mockThread} disabled={true} />);
    expect(mockPromptDropdownProps.disabled).toBe(true);
  });
});
